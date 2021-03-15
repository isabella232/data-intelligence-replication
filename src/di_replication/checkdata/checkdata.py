

import io
import logging
import os
import subprocess

import pandas as pd

import sdi_utils.gensolution as gs


try:
    api
except NameError:
    class api:
        class Message:
            def __init__(self, body=None, attributes=""):
                self.body = body
                self.attributes = attributes

        def send(port, msg):
            if isinstance(msg, api.Message):
                print('{}: {}'.format(port, msg.body))
            else:
                print('{}: {}'.format(port, msg))

        class config:
            ## Meta data
            config_params = dict()
            tags = {}
            version = "0.1.0"
            operator_name = 'checkdata'
            operator_description = "Check Data"
            operator_description_long = "Check if data is on input port."
            add_readme = dict()

            transform = True
            config_params['transform'] = {'title': 'Transform data', \
                                          'description':'Transform data defined in if clause of script.',\
                                          'type': 'boolean'}

        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(name=config.operator_name)


log_stream = io.StringIO()
sh = logging.StreamHandler(stream=log_stream)
sh.setFormatter(logging.Formatter('%(asctime)s , %(name)s , %(message)s', datefmt='%H,%M,%S'))
api.logger.addHandler(sh)


def on_input(msg):
    att = dict(msg.attributes)

    ### IF SELECT provided data
    if not msg.body == None:

        # Remove columns 'DIREPL_PID', 'DIREPL_STATUS' and create JSON
        header = [c["name"] for c in msg.attributes['table']['columns']]
        df = pd.DataFrame(msg.body, columns=header).drop(columns=['DIREPL_PID', 'DIREPL_STATUS'])

        num_records = df.shape[0]
        msg.body = df.to_json(orient='records', date_format='%Y%m%d %H:%M:%S')

        # Send to data-outport
        api.send("output", api.Message(attributes=att, body=msg.body))

        # Send to log-outport
        api.logger.info("Data send to file. Records: {}, Data: {}".format(num_records, len(msg.body)))
        api.send('log', log_stream.getvalue())
        log_stream.seek(0)
        log_stream.truncate()

    ### No data from SELECT
    else:
        msg.body = 'NODATA'

        # Send to Nodata-port
        api.send("nodata", msg)

        # Send to log-outport
        api.logger.info("No Data send!")
        api.send('log', log_stream.getvalue())
        log_stream.seek(0)
        log_stream.truncate()


inports = [{'name': 'input', 'type': 'message.table', "description": "data"}]
outports = [{'name': 'log', 'type': 'string', "description": "Logging data"}, \
            {'name': 'output', 'type': 'message.file', "description": "data"},
            {'name': 'nodata', 'type': 'message.file', "description": "no data"}]

#api.set_port_callback("input", on_input)


def test_operator():

    ## table input
    headers = ["header1","header2","header3","DIREPL_STATUS","DIREPL_PID" ]
    attributes = {"table":{"columns":[{"class":"string","name":headers[0],"nullable":True,"size":80,"type":{"hana":"NVARCHAR"}},
                                      {"class":"string","name":headers[1],"nullable":True,"size":3,"type":{"hana":"NVARCHAR"}},
                                      {"class":"string","name":headers[2],"nullable":True,"size":10,"type":{"hana":"NVARCHAR"}},
                                      {"class":"string","name":headers[3],"nullable":True,"size":1,"type":{"hana":"NVARCHAR"}},
                                      {"class":"integer","name":headers[4],"nullable":True,"type":{"hana":"BIGINT"}}],
                           "name":"test.table","version":1},
                  'base_table':'TABLE','schema_name':'schema','table_name':'table','message.lastBatch':False}

    table = [[(j * 3 + i) for i in range(0, len(headers))] for j in range(0, 5)]
    msg = api.Message(attributes=attributes, body=table)
    on_input(msg)



if __name__ == '__main__':
    test_operator()
    if True :
        basename = os.path.basename(__file__[:-3])
        package_name = os.path.basename(os.path.dirname(os.path.dirname(__file__)))
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        solution_name = '{}_{}.zip'.format(basename, api.config.version)
        package_name_ver = '{}_{}'.format(package_name, api.config.version)

        solution_dir = os.path.join(project_dir, 'solution/operators', package_name_ver)
        solution_file = os.path.join(project_dir, 'solution/operators', solution_name)

        # rm solution directory
        subprocess.run(["rm", '-r', solution_dir])

        # create solution directory with generated operator files
        gs.gensolution(os.path.realpath(__file__), api.config, inports, outports)

        # Bundle solution directory with generated operator files
        subprocess.run(["vctl", "solution", "bundle", solution_dir, "-t", solution_file])