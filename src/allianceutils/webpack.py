import json
import logging
import time
from typing import Dict
from typing import Optional
from typing import Sequence
from urllib.parse import ParseResult
from urllib.parse import quote
from urllib.parse import urljoin
from urllib.parse import urlparse

from django.conf import settings
from django.templatetags.static import static

logger = logging.Logger('webpack')

# Number of seconds before warning about slow build
# Helps catch broken dev servers and confusing devs about why requests are loading
WEBPACK_DEV_LOADING_TIME_WARNING_DELAY = 20


def get_chunk_tags(chunks: Dict, attrs: str):
    """
    Get tags for
    :param chunks:
    :param attrs:
    :return:
    """
    tags = []
    for chunk in chunks:
        resource_type = chunk['resource_type']
        original_url = chunk['url']

        parse_result = urlparse(original_url)
        path = parse_result.path
        # If under STATIC_URL rewrite using static tag so that we respect static file storage
        # options, eg. ManifestStaticFileStorage
        if settings.STATIC_URL and path.startswith(settings.STATIC_URL):
            try:
                path = static(path[len(settings.STATIC_URL):])
            except ValueError:
                # Allow url's that aren't managed by static files - eg. this will happen
                # for ManifestStaticFileStorage if file is not in the manifest
                pass
        url = ParseResult(**dict(parse_result._asdict(), path=path)).geturl()
        if resource_type == 'js':
            tags.append(f'<script type="text/javascript" src="{url}" {attrs}></script>')
        if resource_type == 'css':
            tags.append(f'<link type="text/css" href="{url}" rel="stylesheet" {attrs}/>')
    return tags

config_defaults = {
    "INCLUDE_QUERY_HASH": True,
    "BASE_URL": None,
}

class WebpackEntryPointLoader:

    extensions_by_resource_type = {
        'js': ('js', 'js.gz'),
        'css': ('css', 'css.gz'),
    }

    config: Dict

    def __init__(self, config: Dict):
        self.config = {**config_defaults, **config}

    def load_stats(self) -> Dict:
        """
        Example of valid json file strucures:
        When compiling:

        {
          "status": "compiling",
        }

        Error:
        {
          "status": "error",
          "resource": "/path/to/file.js",
          "error": "ModuleBuildError",
          "message": "Module build failed <snip>"
        }

        Compiled:
        {
          "status": "done",
          "entrypoints": {
            "admin": [
              {
                "name": "runtime.bundle.js",
                "contentHash": "e2b781da02d36dad3aff"
              },
              {
                "name": "vendor.bundle.js",
                "contentHash": "774c52f57ce30a5e1382"
              },
              {
                "name": "common.bundle.js",
                "contentHash": "639269b921c8cf869c5f"
              },
              {
                "name": "common.bundle.css",
                "contentHash": "d60a0fa36613ea58a23d"
              }
              {
                "name": "admin.bundle.js",
                "contentHash": "c78fb252d4e00207afef"
              },
            ],
            "app": [
              {
                "name": "runtime.bundle.js",
                "contentHash": "e2b781da02d36dad3aff"
              },
              {
                "name": "vendor.bundle.js",
                "contentHash": "774c52f57ce30a5e1382"
              },
              {
                "name": "common.bundle.js",
                "contentHash": "639269b921c8cf869c5f"
              },
              {
                "name": "common.bundle.css",
                "contentHash": "d60a0fa36613ea58a23d"
              },
              {
                "name": "app.bundle.js",
                "contentHash": "806fc65dbad8a4dbb1cc"
              },
            ]
          },
          "publicPath": "http://hostname/"
        }
        :return: Dict
        """
        with open(self.config['STATS_FILE'], encoding="utf-8") as f:
            stats = json.load(f)
            if stats['status'] not in ['error', 'compiling', 'done']:
                raise ValueError('Badly formatted stats file received')
            return stats

    def get_resource_type(self, chunk: Dict) -> Optional[str]:
        for resource_type, extensions in self.extensions_by_resource_type.items():
            if chunk['name'].endswith(extensions):
                return resource_type
        return None

    def get_chunk_url(self, public_path: str, chunk: Dict) -> str:
        name = chunk['name']
        query = ''
        if self.config['INCLUDE_QUERY_HASH'] and chunk.get('contentHash'):
            query = f'?{chunk["contentHash"]}'
        path = f'{public_path}{name}{query}'
        if self.config['BASE_URL']:
            return urljoin(self.config['BASE_URL'], path)
        return path

    def filter_chunks(self, public_path: str, chunks: Sequence[Dict], required_resource_type:str) -> Sequence[Dict]:
        if required_resource_type not in self.extensions_by_resource_type:
            valid_resource_types = ', '.join(self.extensions_by_resource_type.keys())
            raise ValueError(f'Invalid chunk type {required_resource_type}. Must be one of: {valid_resource_types}')
        for chunk in chunks:
            resource_type = self.get_resource_type(chunk)
            if required_resource_type == resource_type:
                yield {
                    'url': self.get_chunk_url(public_path, chunk),
                    'resource_type': resource_type,
                    **chunk,
                }

    def get_chunks_for_entry_point(self, entry_point_name:str, resource_type:str) -> Sequence[Dict]:
        stats = self.load_stats()
        if stats['status'] == 'compiling':
            logger.warning('Webpack is compiling... web requests will wait until this resolves before loading')
            start = time.time()
            warning_logged = False
            while stats['status'] == 'compiling':
                time.sleep(0.1)
                stats = self.load_stats()
                if not warning_logged and (time.time() - start) > WEBPACK_DEV_LOADING_TIME_WARNING_DELAY:
                    logger.warning('Webpack appears to be taking a while to build. Check your webpack devserver is running and has not crashed')
                    warning_logged = True
            logger.warning('Webpack compilation complete!')

        if stats['status'] == 'error':
            error = f"""
            {stats['error']} in {stats['resource']}

            {stats['message']}
            """
            raise ValueError(error)

        entry_point = stats['entrypoints'].get(entry_point_name)
        if not entry_point:
            known_entry_points = ', '.join(stats['entrypoints'].keys())
            raise ValueError(f'Invalid entry point {entry_point_name}. Known entry points: {known_entry_points}')
        public_path = stats.get('publicPath', '')

        return self.filter_chunks(public_path, entry_point, resource_type)
