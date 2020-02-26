import argparse
import getpass
import logging
import smtplib
import ssl
import time
#import slack
import os
from urllib.parse import quote

import tableauserverclient as TSC
import yaml

from workbook_api import workbook_metrics


def main():
    parser = argparse.ArgumentParser(description='Access to config.yml file')
    parser.add_argument('--config-file', '-c', default='config.yml',
                        help='config file path. Default is config.yml')

    args = parser.parse_args()
    # Load yml config file
    try:
        with open(args.config_file, 'r') as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    except:
        raise
        

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

        # Search for workbooks based on the rejected tag
        req_option = TSC.RequestOptions()
        req_option.filter.add(TSC.Filter(TSC.RequestOptions.Field.Tags,
                                         TSC.RequestOptions.Operator.Equals,
                                         quote(cfg['tags']['reject_tag'], safe='')))

        # For each wb found we will run a number of checks to determine if the
        for wb in TSC.Pager(server.workbooks, req_option):

            print("-------- Starting checks for wb: {0} --------".format(wb.name))

            # Download the workbook without extract to perform the checks
            file_path = server.workbooks.download(wb.id, no_extract=True)
            result = workbook_metrics(file_path, wb.name)
            # Get the wb owner's details
            author = server.users.get_by_id(wb.owner_id)
            # OPTION 1 share the feedback to your users via email
            author_email = author.email
            message = """
            Subject: Workbook rejected for migration.

            Your workbook {0} was identified as poor performant or exceeded the max number of views allowed for migration: {1}.
            Here is the detailed information of your workbook:
            {2}
            Please review it with your Tableau admin to find ways to improve the performance of your Dashboard.
            """.format(wb.name, cfg['performance_thresholds']['max_views'], result)

            if (author_email is None):
                author_email = 'YOUR_DEFAULT_EMAIL@EMAIL.COM'

            try:
                # TODO: if running on SSL then you will need to Create a secure SSL context and login to your server
                # context = ssl.create_default_context()

                with smtplib.SMTP(host=cfg['smtp']['smtp_host'], port=cfg['smtp']['smtp_port']) as smtpObj:
                    # smtpObj.login(user=cfg['smtp']['smtp_user'], password=cfg['smtp']['smtp_password'])
                    smtpObj.sendmail(from_addr=cfg['smtp']['smtp_from_email'],
                                     to_addrs=[author_email],
                                     msg=message)
            except Exception as e:
                print("Error: unable to send email: {0}".format(e))

            # OPTION 2 uncomment to share the feedback to your users via an slack message. Make sure you
            # also uncomment the import!
            
            # try:
            #     slack_client = slack.WebClient(token=cfg['slack']['slack_token'])
            #     slack_client.chat_postMessage(
            #                                   channel=cfg['slack']['slack_channel'],
            #                                   text=message)
            # except Exception as e:
            #     print("Error: unable to send slack message: {0}".format(e))
            
            # always clean your files!
            os.remove(file_path)

            print(result)

if __name__ == '__main__':
    main()