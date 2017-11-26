import os, re
from collections import OrderedDict, Counter, defaultdict
from mmap import mmap

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

    def load( self, target_path, verbose=False ):
        #target_path = os.path.abspath( target_path )
        for root, subFolders, files in os.walk( target_path ):
            for f in files:
                full_path = os.path.join( root, f )

                for key, regex in self.file_re_map.items():
                    match = regex.search( full_path )
                    if match:
                        self._files[full_path] = {
                            'klass': self.file_class_map[key],
                            're': key,
                            'match': match.groups()
                        }
                        if not self.case_sensitive:
                            self._files[full_path]['match'] = tuple([x.upper() for x in self._files[full_path]['match']])

        if self.unique_matches:
            unique_check = {k:v for k, v in Counter([x['match'] for x in self._files.values()]).items() if v > 1}
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
        for path in load_order:
            info = self._files[path]
            with open( path, 'r+b' ) as f:
                data = mmap( f.fileno(), 0 )
                if verbose:
                    print( '{} => {}'.format( path, info['klass'] ) )

                deps = {attr: self._files[dest]['obj'] for dest, attr in dependency_map[path]}

                info['obj'] = info['klass']( data, preload_attrs=deps )
                data.close()


        self.post_load( verbose )
        return

    def post_load( self, verbose=False ):
        pass
        
    def save_file( self, target, verbose=False ):
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
