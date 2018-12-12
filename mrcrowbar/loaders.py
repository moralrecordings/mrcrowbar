import os, re
from collections import OrderedDict, Counter, defaultdict
from mmap import mmap
import logging
logger = logging.getLogger( __name__ )


class Archive( object ):
    def __init__( self ):
        pass

    def close( self ):
        pass

    def get_meta( self ):
        pass

    def list_files( self, path=None, recurse=True ):
        pass

    def list_paths( self, path=None, recurse=True ):
        pass
    
    def get_file_meta( self, path ):
        pass

    def get_file( self, path ):
        pass

    def get_path_meta( self, path ):
        pass


class FileSystem( Archive ):
    def __init__( self, base_path ):
        self.base_path = os.path.abspath( base_path )

    def _to_internal( self, path ):
        assert path.startswith( self.base_path )
        return '.'+path[len( self.base_path ):]+os.path.sep

    def _from_internal( self, path ):
        assert path.startswith( '.'+os.path.sep )
        return self.base_path + path[1:]

    def list_paths( self, path=None, recurse=True ):
        results = []
        base = self.base_path if path is None else self._from_internal( path )

        if not recurse:
            _, sub_folders, _ = next( os.walk( base ) )
            results = [self._to_internal( root ) for root in sub_folders]
        else:
            for root, sub_folders, files in os.walk( base ):
                results.append( self._to_internal( root ) )
        return results

    def list_files( self, path=None, recurse=True ):
        results = []
        base = self.base_path if path is None else self._from_internal( path )
        if not recurse:
            _, _, files = next( os.walk( base ) )
            results = [self._to_internal( f ) for f in files]
        else:
            for root, sub_folders, files in os.walk( base ):
                for f in files:
                    results.append( self._to_internal( root )+f )
        return results
    
    def get_file( self, path ):
        # TODO: something nicer involving mmap?
        return open( self._from_internal( path ), 'r+b' )


class Loader( object ):
    _SEP = re.escape( os.path.sep )

    def __init__( self, file_class_map, dependency_list=None, case_sensitive=False, unique_matches=True ):
        self.file_class_map = file_class_map
        self.dependency_list = dependency_list
        self.case_sensitive = case_sensitive
        self.unique_matches = unique_matches
        self.re_flags = re.IGNORECASE if not case_sensitive else 0
        self.file_re_map = { key: re.compile( key, flags=self.re_flags ) for key, klass in file_class_map.items() if klass } 
        self._files = OrderedDict()

    def load( self, target_path ):
        #target_path = os.path.abspath( target_path )
        self.fs = FileSystem( target_path )
        for f in self.fs.list_files():

            for key, regex in self.file_re_map.items():
                match = regex.search( f )
                if match:
                    self._files[f] = {
                        'klass': self.file_class_map[key],
                        're': key,
                        'match': match.groups()
                    }
                    if not self.case_sensitive:
                        self._files[f]['match'] = tuple( [x.upper() for x in self._files[f]['match']] )

        if self.unique_matches:
            unique_check = {k:v for k, v in Counter( [x['match'] for x in self._files.values()] ).items() if v > 1}
            if unique_check:
                extras = []
                for name, file in self._files.items():
                    if file['match'] in unique_check:
                        extras.append( name )

                self._files = {}
                raise Exception( 'Multiple filename matches found for the same source: {}'.format( ', '.join( extras ) ) ) 

        dependencies = []
        
        if self.dependency_list:
            for i, (consumer, dependency, format, attr) in enumerate( self.dependency_list ):
                consumer_re = re.compile( consumer, flags=self.re_flags )
                dependency_re = re.compile( dependency, flags=self.re_flags )
                consumer_matches = []
                dependency_matches = []
                if not self.case_sensitive:
                    format = tuple([x.upper() for x in format])

                for path in self._files:
                    consumer_match = consumer_re.search( path )
                    dependency_match = dependency_re.search( path )
                    if consumer_match and dependency_match:
                        self._files = {}
                        raise Exception( 'Problem parsing dependencies: path {} matches for both consumer ({}) and dependency ({})'.format( path, consumer, dependency ) )
                    elif consumer_match:
                        groups = consumer_match.groups()
                        if not self.case_sensitive:
                            groups = tuple([x.upper() for x in groups])
                        consumer_matches.append( (path, groups) )
                    elif dependency_match:
                        groups = dependency_match.groups()
                        if not self.case_sensitive:
                            groups = tuple([x.upper() for x in groups])
                        dependency_matches.append( (path, groups) )

                for path, groups in consumer_matches:
                    target_groups = tuple([x.format( *groups ) for x in format])
                    if not self.case_sensitive:
                        target_groups = tuple([x.upper() for x in target_groups])
                    targets = [x[0] for x in dependency_matches if x[1] == target_groups]
                    if len( targets ) > 1:
                        self._files = {}
                        raise Exception( 'Problem parsing dependencies: path {} has multiple matches for dependency {} ({})'.format( path, attr, ', '.join( targets ) ) )
                    elif len( targets ) == 1:
                        dependencies.append( (i, path, targets[0]) )
        
        # make dependency lookup table
        dependency_map = defaultdict( list )
        for index, source, dest in dependencies:
            dependency_map[source].append( (dest, self.dependency_list[index][3]) )

        # model the dependency tree
        head_count = defaultdict( int )
        tails = defaultdict( list )
        heads = []
        for index, tail, head in dependencies:
            head_count[tail] += 1
            if head in tails:
                tails[head].append( tail )
            else:
                tails[head] = [tail]
                heads.append( head )

        load_order = [h for h in heads if h not in head_count]
        for head in load_order:
            for tail in tails[head]:
                head_count[tail] -= 1
                if not head_count[tail]:
                    load_order.append( tail )
        loop = [n for n, heads in head_count.items() if heads]
        if loop:
            self._files = {}
            raise Exception( 'Problem parsing dependencies: loop detected' )

        load_order += [x for x in self._files.keys() if x not in load_order]

        # load files in based on dependency sorted list order
        logger.info( '{}: loading files'.format( self ) )
        for path in load_order:
            info = self._files[path]
            with self.fs.get_file( path ) as f:
                data = mmap( f.fileno(), 0 )
                logger.info( '{} => {}'.format( path, info['klass'] ) )

                deps = {attr: self._files[dest]['obj'] for dest, attr in dependency_map[path]}

                info['obj'] = info['klass']( data, preload_attrs=deps )
                data.close()


        self.post_load()
        return

    def post_load( self ):
        pass
        
    def save_file( self, target ):
        assert target in self._files
        export = self._files[target]['obj'].export_data()
        with open( target, 'wb' ) as out:
            out.write( export )
        return

    def keys( self ):
        return self._files.keys()

    def __len__( self ):
        return len( self._files )

    def __getitem__( self, key ):
        return self._files[key]['obj']

    def __contains__( self, key ):
        return key in self._files
