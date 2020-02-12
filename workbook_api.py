# workbook_metrics() returns a summary with workbook metrics in a dict structure
# For example:
# {
#   'custom_sql': False,
#   'dashboards': 6,
#   'datasources': 3,
#   'views': 21,
#   'max_calc_len': 6,
#   'max_field_count': 33,
#   'max_quick_filter_count': 6
# }
#
# custom_sql -               if custom SQL was found in any data source (boolean)
# dashboards -               total number of dashboards
# datasources -              total number of data sources
# views -                    total number of views, including hidden views
# max_calc_len -             max number of lines found in any calculated field in any data source
# max_field_count -          max number of fields found in any data source, including hidden fields
# max_quick_filter_count -   max number of quick filters found in any dashboard
from lxml import etree
from io import BytesIO
from zipfile import ZipFile


def workbook_metrics(filename,wb_name):

    if filename.endswith('.twb'):
        in_file = open(filename, "rb")
        xml = in_file.read()

    elif filename.endswith('.twbx'):
        input_zip=ZipFile(filename)
        # the original twb file in the twbx may have a different name. We loop the files inside the zip looking for a twb
        for zipMember in input_zip.filelist:
            if (zipMember.filename.endswith("twb")):
                twb = zipMember.filename
                xml = input_zip.read(twb)
                break

    doc = etree.parse(BytesIO(xml))
    root = doc.getroot()

    result = dict()
    result['custom_sql'] = bool(root.xpath(".//relation[@name='Custom SQL Query']"))
    result['dashboards'] = len(root.xpath(".//dashboard"))
    result['datasources'] = len(root.xpath("/workbook/datasources/datasource/@caption"))
    result['views'] = len(root.xpath(".//worksheet"))

    max_calc_len = 0
    calcs = root.xpath(".//calculation/@formula")
    for calc in calcs:
        max_calc_len = max(max_calc_len, 1 + calc.count('\n'))
    result['max_calc_len'] = max_calc_len

    max_field_count = 0
    datasources = root.xpath("/workbook/datasources/datasource")
    for datasource in datasources:
        max_field_count = max(max_field_count, len(datasource.xpath("./column")))
    result['max_field_count'] = max_field_count

    max_quick_filter_count = 0
    dashboards = root.xpath(".//dashboard")
    for dashboard in dashboards:
        max_quick_filter_count = max(max_quick_filter_count, len(dashboard.xpath("./zones//zone[@type='filter']")))
    result['max_quick_filter_count'] = max_quick_filter_count

    return result


