# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Max Maisel / Hildo Guillardi Júnior
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Author information.
__author__ = 'XESS Corporation'
__webpage__ = 'info@xess.com'

# Python2/3 compatibility.
#from __future__ import (unicode_literals, print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()

# Libraries.
import json, requests
import logging, tqdm
import copy, re
from collections import Counter
from urllib.parse import quote_plus as urlquote

# KiCost definitions.
from ..global_vars import logger, DEBUG_OVERVIEW, DEBUG_OBSESSIVE  # Debug configurations.
from ..global_vars import SEPRTR

# Distributors definitions.
from .distributor import distributor_class
from .global_vars import * # Debug information, `distributor_dict` and `SEPRTR`.

OCTOPART_MAX_PARTBYQUERY = 20 # Maximum part list length to one single query.

__all__ = ['api_octopart']

class api_octopart(distributor_class):

    @staticmethod
    def init_dist_dict():
        dists = {
            'arrow': {
                'module': 'arrow', # The directory name containing this file.
                'type': 'web', # Allowable values: 'local' or 'web'.
                'order': {
                    'cols': ['part_num', 'purch', 'refs'], # Sort-order for online orders.
                    'delimiter': ',', # Delimiter for online orders.
                    'not_allowed_char': ',', # Characters not allowed at the BoM for web-site import.
                    'replace_by_char': ';', # The `delimiter` is not allowed inside description. This caracter is used to replace it.
                },
                'label': {
                    'name': 'Arrow',  # Distributor label used in spreadsheet columns.
                    # Formatting for distributor header in worksheet; bold, font and align are
                    # `spreadsheet.py` defined but can by overload heve.
                    'format': {'font_color': 'white', 'bg_color': '#000000'}, # Arrow black.
                    'url': 'https://www.arrow.com/',
                },
            },
            'digikey': {
                'module': 'digikey', 'type': 'web',
                'order': {
                    'cols': ['purch', 'part_num', 'refs'],
                    'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'Digi-Key',
                    'format': {'font_color': 'white', 'bg_color': '#CC0000'}, # Digi-Key red.
                    'url': 'https://www.digikey.com/',
                },
            },
            'farnell': {
                'module': 'farnell', 'type': 'web',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'Farnell',
                    'format': {'font_color': 'white', 'bg_color': '#FF6600'}, # Farnell/E14 orange.
                    'url': 'https://www.newark.com/',
                },
            },
            'mouser': {
                'module': 'mouser', 'type': 'web',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': '|', 'not_allowed_char': '| ', 'replace_by_char': ';_',
                },
                'label': {
                    'name': 'Mouser', 
                    'format': {'font_color': 'white', 'bg_color': '#004A85'}, # Mouser blue.
                    'url': 'https://www.mouser.com',
                },
            },
            'newark': {
                'module': 'newark', 'type': 'web',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'Newark',
                    'format': {'font_color': 'white', 'bg_color': '#A2AE06'}, # Newark/E14 olive green.
                    'url': 'https://www.newark.com/',
                },
            },
            'rs': {
                'module': 'rs', 'type': 'web',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'RS Components',
                    'format': {'font_color': 'white', 'bg_color': '#FF0000'}, # RS Components red.
                    'url': 'https://uk.rs-online.com/',
                },
            },
            'tme': {
                'module': 'tme', 'type': 'web',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'TME',
                    'format': {'font_color': 'white', 'bg_color': '#0C4DA1'}, # TME blue
                    'url': 'https://www.tme.eu',
                },
            },
        }
        if not 'enabled' in distributors_modules_dict['api_octopart']:
             # First module load.
            distributors_modules_dict.update({'api_octopart': {
                                            'type': 'api', # Module type, could be 'api', 'scrape' or 'local'.
                                            'url': 'https://octopart.com/', # Web site API information.
                                            'distributors': dists.keys(), # Avaliable web distributors in this api.
                                            'enabled': False, # Default status of the module (it's load but can be not calle).
                                            'param': 'Token', # Configuration parameters.
                                            'dist_translation': { # Distributor translation.
                                                                    'arrow': 'Arrow Electronics, Inc.',
                                                                    'digikey': 'Digi-Key',
                                                                    'farnel': 'Farnell',
                                                                    'mouser': 'Mouser',
                                                                    'newark': 'Newark',
                                                                    'rs': 'RS Components',
                                                                    'newark': ,
                                                                    'tme': 'TME'
                                                                }
                                                }
                                            })
        # Update the `distributor_dict`with the available distributor in this module with the module is enabled.
        # It can be not enabled by the GUI saved configurations.
        if distributors_modules_dict['api_partinfo_kitspace']['enabled']:
            distributor_dict.update(dists)


    def query(query, apiKey=None):
        """Send query to Octopart and return results."""
        #url = 'http://octopart.com/api/v3/parts/match'
        #payload = {'queries': json.dumps(query), 'include\[\]': 'specs', 'apikey': token}
        #response = requests.get(url, params=payload)
        if apiKey:
            url = 'http://octopart.com/api/v3/parts/match?queries=%s' \
            % json.dumps(query)
            url += '&apikey=' + apiKey
        else:
            url = 'https://temp-octopart-proxy.kitspace.org/parts/match?queries=%s' \
            % json.dumps(query)
        url += '&include[]=specs'
        url += '&include[]=datasheets'
        response = requests.get(url)
        if response.status_code == requests.codes['ok']:
            results = json.loads(response.text).get('results')
            return results
        elif response.status_code == requests.codes['not_found']: #404
            raise Exception('Octopart server not found.')
        elif response.status_code == 403:
            raise Exception('Octopart KEY invalid, registre one at "https://www.octopart.com".')
        else:
            raise Exception('Octopart error: ' + str(response.status_code))


    def sku_to_mpn(sku, apiKey):
        """Find manufacturer part number associated with a distributor SKU."""
        part_query = [{'reference': 1, 'sku': urlquote(sku)}]
        results = api_octopart.query(part_query, apiKey)
        if not results:
            return None
        result = results[0]
        mpns = [item['mpn'] for item in result['items']]
        if not mpns:
            return None
        if len(mpns) == 1:
            return mpns[0]
        mpn_cnts = Counter(mpns)
        return mpn_cnts.most_common(1)[0][0]  # Return the most common MPN.


    def skus_to_mpns(parts, distributors):
        """Find manufaturer's part number for all parts with just distributor SKUs."""
        for i, part in enumerate(parts):

            # Skip parts that already have a manufacturer's part number.
            if part.fields.get('manf#'):
                continue

            # Get all the SKUs for this part.
            skus = list(
                set([part.fields.get(dist + '#', '') for dist in distributors]))
            skus = [sku for sku in skus
                    if sku not in ('', None)]  # Remove null SKUs.

            # Skip this part if there are no SKUs.
            if not skus:
                continue

            # Convert the SKUs to manf. part numbers.
            mpns = [api_octopart.sku_to_mpn(sku, apiKey) for sku in skus]
            mpns = [mpn for mpn in mpns
                    if mpn not in ('', None)]  # Remove null manf#.

            # Skip assigning manf. part number to this part if there aren't any to assign.
            if not mpns:
                continue

            # Assign the most common manf. part number to this part.
            mpn_cnts = Counter(mpns)
            part.fields['manf#'] = mpn_cnts.most_common(1)[0][0]


    def query_part_info(parts, distributors, currency=DEFAULT_CURRENCY, apiKey=None):
        """Fill-in the parts with price/qty/etc info from Octopart."""
        logger.log(DEBUG_OVERVIEW, '# Getting part data from Octopart...')

        # Setup progress bar to track progress of Octopart queries.
        progress = tqdm.tqdm(desc='Progress', total=len(parts), unit='part', miniters=1)

        # Change the logging print channel to `tqdm` to keep the process bar to the end of terminal.
        class TqdmLoggingHandler(logging.Handler):
            '''Overload the class to write the logging through the `tqdm`.'''

            def __init__(self, level=logging.NOTSET):
                super(self.__class__, self).__init__(level)

            def emit(self, record):
                try:
                    msg = self.format(record)
                    tqdm.tqdm.write(msg)
                    self.flush()
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    self.handleError(record)
                pass

        # Get handles to default sys.stdout logging handler and the
        # new "tqdm" logging handler.
        logDefaultHandler = logger.handlers[0]
        logTqdmHandler = TqdmLoggingHandler()

        # Replace default handler with "tqdm" handler.
        logger.addHandler(logTqdmHandler)
        logger.removeHandler(logDefaultHandler)

        # Translate from Octopart distributor names to the names used internally by kicost.
        dist_xlate = distributors_modules_dict['api_octopart']['dist_translation']

        def get_part_info(query, parts, currency='USD'):
            """Query Octopart for quantity/price info and place it into the parts list."""

            results = api_octopart.query(query, apiKey)

            # Loop through the response to the query and enter info into the parts list.
            for result in results:
                i = int(result['reference'])  # Get the index into the part dict.
                # Loop through the offers from various dists for this particular part.
                for item in result['items']:

                    # Assign the lifecycle status 'obsolete' (others possible: 'active'
                    # and 'not recommended for new designs') but not used.
                    if 'lifecycle_status' in item['specs']:
                        lifecycle_status = item['specs']['lifecycle_status']['value'][0].lower()
                        if lifecycle_status == 'obsolete':
                            parts[i].lifecycle = lifecycle_status

                    # Take the datasheet provided by the distributor. This will by used
                    # in the output spreadsheet if not provide any in the BOM/schematic.
                    # This will be signed in the file.
                    if item['datasheets']:
                        parts[i].datasheet = item['datasheets'][0]['url']

                    for offer in item['offers']:

                        # Get the distributor who made the offer and add their
                        # price/qty info to the parts list if its one of the accepted distributors.
                        dist = dist_xlate.get(offer['seller']['name'], '')
                        if dist in distributors:

                            # Get pricing information from this distributor.
                            try:
                                price_tiers = {} # Empty dict in case of exception.
                                dist_currency = list(offer['prices'].keys())
                                parts[idx].currency[dist] = dist_currency[0]
                                price_tiers = {qty: float( price )
                                                    for qty, price in list(offer['prices'].values())[0]
                                                }
                                # Combine price lists for multiple offers from the same distributor
                                # to build a complete list of cut-tape and reeled components.
                                if not dist in parts[idx].price_tiers:
                                    parts[idx].price_tiers[dist] = {}
                                parts[i].price_tiers[dist].update(price_tiers)
                            except Exception:
                                pass  # Price list is probably missing so leave empty default dict in place.

                            # Compute the quantity increment between the lowest two prices.
                            # This will be used to distinguish the cut-tape from the reeled components.
                            try:
                                part_break_qtys = sorted(price_tiers.keys())
                                part_qty_increment = part_break_qtys[1] - part_break_qtys[0]
                            except Exception:
                                # This will happen if there are not enough entries in the price/qty list.
                                # As a stop-gap measure, just assign infinity to the part increment.
                                # A better alternative may be to examine the packaging field of the offer.
                                part_qty_increment = float("inf")

                            # Use the qty increment to select the part SKU, web page, and available quantity.
                            # Do this if this is the first part offer from this dist.
                            if not parts[i].part_num[dist]:
                                parts[i].part_num[dist] = offer.get('sku', '')
                                parts[i].url[dist] = offer.get('product_url', '')
                                parts[i].qty_avail[dist] = offer.get(
                                    'in_stock_quantity', None)
                                parts[i].qty_increment[dist] = part_qty_increment
                            # Otherwise, check qty increment and see if its the smallest for this part & dist.
                            elif part_qty_increment < parts[i].qty_increment[dist]:
                                # This part looks more like a cut-tape version, so
                                # update the SKU, web page, and available quantity.
                                parts[i].part_num[dist] = offer.get('sku', '')
                                parts[i].url[dist] = offer.get('product_url', '')
                                parts[i].qty_avail[dist] = offer.get(
                                    'in_stock_quantity', None)
                                parts[i].qty_increment[dist] = part_qty_increment

                            # Don't bother with any extra info from the distributor.
                            parts[i].info_dist[dist] = {}

        # Get the valid distributors names used by them part catalog
        # that may be index by Octopart. This is used to remove the
        # local distributors and future not implemented in the Octopart
        # definition.
        distributors_octopart = [d for d in distributors if distributors[d]['type']=='web'
                            and distributors_modules_dict['api_octopart'].get('dist_translation')]

        # Break list of parts into smaller pieces and get price/quantities from Octopart.
        octopart_query = []
        prev_i = 0 # Used to record index where parts query occurs.
        for i, part in enumerate(parts):

            # Create an Octopart query using the manufacturer's part number or 
            # distributor SKU.
            manf_code = part.fields.get('manf#')
            if manf_code:
                part_query = {'reference': i, 'mpn': urlquote(manf_code)}
            else:
                try:
                    # No MPN, so use the first distributor SKU that's found.
                    #skus = [part.fields.get(d + '#', '') for d in distributors_octopart
                    #            if part.fields.get(d + '#') ]
                    for octopart_dist_sku in distributors_octopart:
                        sku = part.fields.get(octopart_dist_sku + '#', '')
                        if sku:
                            break
                    # Create the part query using SKU matching.
                    part_query = {'reference': i, 'sku': urlquote(sku)}
                    
                    # Because was used the distributor (enrolled at Octopart list)
                    # despite the normal 'manf#' code, take the sub quantity as
                    # general sub quantity of the current part.
                    try:
                        part.fields['manf#_qty'] = part.fields[octopart_dist_sku + '#_qty']
                        logger.warning("Associated {q} quantity to '{r}' due \"{f}#={q}:{c}\".".format(
                                q=part.fields[octopart_dist_sku + '#_qty'], r=part.refs,
                                f=octopart_dist_sku, c=part.fields[octopart_dist_sku+'#']))
                    except:
                        pass
                except IndexError:
                    # No MPN or SKU, so skip this part.
                    continue

            # Add query for this part to the list of part queries.
            octopart_query.append(part_query)

            # Once there are enough (but not too many) part queries, make a query request to Octopart.
            if len(octopart_query) == OCTOPART_MAX_PARTBYQUERY:
                get_part_info(octopart_query, parts)
                progress.update(i - prev_i) # Update progress bar.
                prev_i = i;
                octopart_query = []  # Get ready for next batch.

        # Query Octopart for the last batch of parts.
        if octopart_query:
            get_part_info(octopart_query, parts)
            progress.update(len(parts)-prev_i) # This will indicate final progress of 100%.

        # Restore the logging print channel now that the progress bar is no longer needed.
        logger.addHandler(logDefaultHandler)
        logger.removeHandler(logTqdmHandler)

        # Done with the scraping progress bar so delete it or else we get an
        # error when the program terminates.
        del progress
