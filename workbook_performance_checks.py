import argparse
import getpass
import logging
import time
from urllib.parse import quote

import tableauserverclient as TSC
import yaml


def main():
    parser = argparse.ArgumentParser(description='Access to config.yml file')
    parser.add_argument('--config-file', '-c', required=True,
                        help='config file path. Default is config.yml')

    args = parser.parse_args()
    # Load yml config file
    with open(args.config_file, 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

    if cfg['tableau_server']['password'] is None:
        password = getpass.getpass("Password: ")
    else:
        password = cfg['tableau_server']['password']

    # Set logging level based on user input, or error by default
    logging_level = getattr(logging, cfg['logging_level'].upper())
    logging.basicConfig(level=logging_level)

    tableau_auth = TSC.TableauAuth(cfg['tableau_server']['username'],
                                   password,
                                   cfg['tableau_server']['site'])
    server = TSC.Server(cfg['tableau_server']['server'], use_server_version=True)

    with server.auth.sign_in(tableau_auth):
        # Encode search tags to be url friendly
        encoded_tags = []
        search_tags = cfg['tags']['search_tag'].split(',')
        for tag in search_tags:
            encoded_tags.append(quote(tag, safe=''))

        # Search for workbooks based on input tags
        req_option = TSC.RequestOptions()
        req_option.filter.add(TSC.Filter(TSC.RequestOptions.Field.Tags,
                                         TSC.RequestOptions.Operator.In,
                                         encoded_tags))

        # For each wb found we will run a number of checks to determine if the
        for wb in TSC.Pager(server.workbooks, req_option):
            # flag to mark if the wb has been marked as rejected for migration
            is_rejected = False
            server.workbooks.populate_views(wb)

            print("-------- Starting checks for wb: {0} --------".format(wb.name))

            # CHECK 1: Validate that the number of views in the wb doesn't exceed the max views threshold
            if len(wb.views) > int(cfg['performance_thresholds']['max_views']):
                print("Number of Max Views exceeded {0} Rejecting workbook {1}".format(len(wb.views), wb.name))
                reject_wb(wb, server, search_tags, cfg['tags']['reject_tag'])
                is_rejected = True
            # CHECK 2: render every view of the wb and validate against the maximum render time threshold
            for view in wb.views:
                if is_rejected:
                    break
                print(" Evaluating: {0} ".format(view.name))
                start_time = time.time()

                # We have a number of different types and functions for each different export type.
                # However, in this case what we want to do is just to populate the view without creating a physical file
                # Therefore, we just unroll simulate the rendering of an image that we can call by using getattr()
                # Note that we use image in order to be able to bypass the cache with the maxage parameter.
                view_req_option = TSC.ImageRequestOptions(imageresolution=TSC.ImageRequestOptions.Resolution.High,
                                                          maxage=1)
                server.views.populate_image(view, view_req_option)
                getattr(view, "image")

                elapsed_time = time.time() - start_time
                print("----render time in seconds --- {0}".format(elapsed_time))
                # Validate the execution time against designated treshold to render view
                is_rejected = elapsed_time > int(cfg['performance_thresholds']['max_elapsed_time'])

                # if the wb is poor performant we tag it as rejected
                if is_rejected:
                    print("Maximum elapsed time exceeded {0} Rejecting workbook {1}".format(elapsed_time, wb.name))
                    reject_wb(wb, server, search_tags, cfg['tags']['reject_tag'])


def reject_wb(wb, server, search_tags, reject_tag):

    """Replace the search tag with a rejection tag to prevent wb to be migrated.
    :param wb: workbook to be rejected
    :param server: the current TSC server with session
    :param search_tags: tags used for search
    :param rejected_tag: tag to set to mark as rejected
    :returns: True
    """

    # remove the search tag to prevent migration
    for tag in search_tags:
        try:
            wb.tags.remove(tag)
            url = "{0}/{1}/tags/{2}".format(server.workbooks.baseurl, wb.id, quote(tag, safe=''))
            server.workbooks.delete_request(url)
        except Exception as e:
            print(e)
            pass
    # set new tag to make it easy to identify. This new tag will be used by the workbook_best_practce_checks if used in conjunction
    new_tag_set = set([reject_tag])
    wb.tags = new_tag_set
    server.workbooks.update(wb)
    return True

if __name__ == '__main__':
    main()
