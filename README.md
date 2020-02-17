# TabValidate ReadMe

TabValidate is meant to be a simple script base to help you perform checks on your Tableau workbooks to validate them against your standards. All checks are done using either Tableau REST API 2019.1+ (https://onlinehelp.tableau.com/current/api/rest_api/en-us/help.htm#REST/rest_api.htm ) or XML scrapping of the workbook.

### Dependencies and how to use

The scripts are Python 2.7 and 3.x compatible. The following are the modules needed for the scripts to run:

* `pip install tableauserverclient`
* `pip install lxml`
* `pip install pyyaml`
* `pip install slackclient` - _Optional_

In order to run any of the scripts you will need to pass the path of the config.yml file.  

`python workbook_best_practice_checks.py --config-file config.yml`

For a sample use case and more ideas on how to use these script please visit the blog on https://community.tableau.com/docs/DOC-24078

