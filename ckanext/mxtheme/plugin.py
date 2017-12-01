import re
import os
import i18n
import logging
import datetime
import urlparse

import ckan.exceptions
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.helpers import sorted_extras
from pylons import config
from slugify import slugify
from ckan.common import request
from routes import url_for as _routes_default_url_for


log = logging.getLogger(__name__)


def format_display_date(time_stamp, format_date="%Y/%m/%d"):
    date_object = datetime.datetime.strptime(time_stamp, "%Y-%m-%dT%H:%M:%S.%f")
    return date_object.strftime(format_date)


def is_regular_format(format):
    return True if format in ['csv', 'xml', 'shp', 'kml', 'kmz', 'json', 'xls', 'txt', 'tls', 'pdf', 'xlsx'] else False


def _add_i18n_to_url(url_to_amend, **kw):
    # If the locale keyword param is provided then the url is rewritten
    # using that locale .If return_to is provided this is used as the url
    # (as part of the language changing feature).
    # A locale of default will not add locale info to the url.

    default_locale = False
    locale = kw.pop('locale', None)
    no_root = kw.pop('__ckan_no_root', False)
    allowed_locales = ['default']
    if locale and locale not in allowed_locales:
        locale = None
    if locale:
        if locale == 'default':
            default_locale = True
    else:
        try:
            locale = request.environ.get('CKAN_LANG')
            default_locale = request.environ.get('CKAN_LANG_IS_DEFAULT', True)
        except TypeError:
            default_locale = True
    try:
        root = request.environ.get('SCRIPT_NAME', '')
        root_aux = root
    except TypeError:
        root = ''

    if kw.get('qualified', False):
        # if qualified is given we want the full url ie http://...
        protocol, host = get_site_protocol_and_host()
        root = _routes_default_url_for('/',
                                       qualified=True,
                                       host=host,
                                       protocol=protocol)[:-1]
    # ckan.root_path is defined when we have none standard language
    # position in the url
    root_path = config.get('ckan.root_path', None)
    root_path_aux = root_path
    if root_path:
        # FIXME this can be written better once the merge
        # into the ecportal core is done - Toby
        # we have a special root specified so use that
        if default_locale:
            root_path = re.sub('/{{LANG}}', '', root_path)
        else:
            root_path = re.sub('{{LANG}}', locale, root_path)
        # make sure we don't have a trailing / on the root
        if len(root_path) > 0:
            if root_path[-1] == '/':
                root_path = root_path[:-1]

        url_path = url_to_amend[len(root):]
        url = '%s%s%s' % (root, root_path if root_aux in root_path_aux else '', url_path)
    else:
        if default_locale:
            url = url_to_amend
        else:
            # we need to strip the root from the url and the add it before
            # the language specification.
            url = url_to_amend[len(root):]
            url = '%s/%s%s' % (root, locale, url)

    # stop the root being added twice in redirects
    if no_root:
        url = url_to_amend[len(root):]
        if not default_locale:
            url = '/%s%s' % (locale, url)

    if url == '/packages':
        error = 'There is a broken url being created %s' % kw
        raise ckan.exceptions.CkanUrlException(error)

    return url


def url(*args, **kw):
    '''Create url adding i18n information if selected
    wrapper for pylons.url'''
    return url_for(*args, **kw)


def get_site_protocol_and_host():
    '''Return the protocol and host of the configured `ckan.site_url`.
    This is needed to generate valid, full-qualified URLs.
    If `ckan.site_url` is set like this::
        ckan.site_url = http://example.com
    Then this function would return a tuple `('http', 'example.com')`
    If the setting is missing, `(None, None)` is returned instead.
    '''
    site_url = config.get('ckan.site_url', None)

    if site_url is not None:
        parsed_url = urlparse.urlparse(site_url)

        netloc = '{0}'.format(parsed_url.netloc.encode('utf-8'))

        return (
            parsed_url.scheme.encode('utf-8'),
            netloc
        )
    return (None, None)


def url_for(*args, **kw):
    '''Return the URL for the given controller, action, id, etc.
    Usage::
        import ckan.plugins.toolkit as toolkit
        url = toolkit.url_for(controller='package', action='read',
                              id='my_dataset')
        => returns '/dataset/my_dataset'
    Or, using a named route::
        toolkit.url_for('dataset_read', id='changed')
    This is a wrapper for :py:func:`routes.url_for` that adds some extra
    features that CKAN needs.
    '''
    locale = kw.pop('locale', None)
    # remove __ckan_no_root and add after to not pollute url
    no_root = kw.pop('__ckan_no_root', False)
    # routes will get the wrong url for APIs if the ver is not provided
    if kw.get('controller') == 'api':
        ver = kw.get('ver')
        if not ver:
            raise Exception('api calls must specify the version! e.g. ver=3')
        # fix ver to include the slash
        kw['ver'] = '/%s' % ver
    if kw.get('qualified', False):
        kw['protocol'], kw['host'] = get_site_protocol_and_host()
    my_url = _routes_default_url_for(*args, **kw)
    kw['__ckan_no_root'] = no_root
    return _add_i18n_to_url(my_url, locale=locale, **kw)


def slugify_name(text):
    """
    Slugifica cualquier texto
    """
    regexs = r'[^-a-zA-z0-9_]+'
    return slugify(text.encode('utf-8'), regex_pattern=regexs) if text is not None else text


def get_adela_endpoint():
    adela_endpoint = os.environ.get("ADELA_ENDPOINT", "http://10.20.55.7/adela/api/v1/distributions")
    return adela_endpoint


def get_grafica_base_url():
    url_grafica_base = os.environ.get("GRAFICA_BASE_URL", "https://cdn.datos.gob.mx/assets/css/main.css")
    return url_grafica_base


def sorted_extras_dgm(extras):
    sorted_list = sorted_extras(extras)
    initial_peroid =final_period = None

    for element in sorted_list:
        log.debug(element)
        if element[0] == 'Inicio del periodo temporal':
            initial_peroid = element

        if element[0] == 'Final del periodo temporal':
            final_period = element

    if initial_peroid is not None and final_period is not None:
        sorted_list.remove(final_period)
        sorted_list.insert(sorted_list.index(initial_peroid) + 1, final_period)

    return sorted_list


class MxthemePlugin(plugins.SingletonPlugin):
    """
    Tema para branding de datos.gob.mx
    en CKAN
    """
    # IConfigurer
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'mxtheme')

    def get_helpers(self):
        """
        Helpers necesarios para el template

        Monkey patching de las funciones:
             - format_display_date
             - is_regular_format
             - url_for
             - url
             - _add_i18n_to_url
        """

        return {
            'format_display_date': format_display_date,
            'is_regular_format': is_regular_format,
            'url_for': url_for,
            'url': url,
            '_add_i18n_to_url': _add_i18n_to_url,
            'slugify_text': slugify_name,
            'get_adela_endpoint': get_adela_endpoint,
            'sorted_extras_dgm': sorted_extras_dgm,
            'get_grafica_base_url': get_grafica_base_url
        }
