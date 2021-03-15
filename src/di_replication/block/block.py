import sdi_utils.gensolution as gs
import os
import subprocess


import logging
import io
import random
from datetime import datetime, timezone
import re

try:
    api
except NameError:
    class api:

        queue = list()

        class Message:
            def __init__(self, body=None, attributes=""):
                self.body = body
                self.attributes = attributes

        def send(port, msg):
            if port == outports[1]['name']:
                api.queue.append(msg)

        class config:
            ## Meta data
            config_params = dict()
            version = '0.1.0'
            tags = {}
            operator_name = 'block'
            operator_description = "Block"

            operator_description_long = "Update replication table status to done."
            add_readme = dict()
            add_readme["References"] = ""

            package_size = '10'
            config_params['package_size'] = {'title': 'Package size',
                                           'description': 'Defining the package size that should be picked for replication. '
                                            'This is not used together with \'Pacakge ID\'',
                                           'type': 'string'}


        format = '%(asctime)s |  %(levelname)s | %(name)s | %(message)s'
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(name=config.operator_name)


# catching logger messages for separate output
log_stream = io.StringIO()
sh = logging.StreamHandler(stream=log_stream)
sh.setFormatter(logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s', datefmt='%H:%M:%S'))
api.logger.addHandler(sh)


def process(msg):
    att = dict(msg.attributes)
    att['operator'] = 'block'

    # Create transaction id
    att['pid'] = int(datetime.utcnow().timestamp() * 1000000)

    package_size = int(api.config.package_size)

    # SQL Statement
    table = att['schema_name'] + '.' + att['table_name']
    if package_size > 0:
        sql = 'UPDATE TOP {packagesize} {table} SET \"DIREPL_STATUS\" = \'B\', \"DIREPL_PID\" = {pid} ' \
              'WHERE  \"DIREPL_STATUS\" = \'W\' OR \"DIREPL_STATUS\" IS NULL '.format(packagesize=package_size, table=table, pid=att['pid'])
    else:
        sql = 'UPDATE {table} SET \"DIREPL_STATUS\" = \'B\', \"DIREPL_PID\" = {pid} ' \
              'WHERE  \"DIREPL_STATUS\" = \'W\' OR \"DIREPL_STATUS\" IS NULL '.format(table=table, pid = att['pid'])

    api.logger.info('Update statement: {}'.format(sql))

    # Send sql to data
    api.send(outports[1]['name'], api.Message(attributes=att, body=sql))

    # Send logging to log-port
    api.send(outports[0]['name'], log_stream.getvalue())
    log_stream.seek(0)
    log_stream.truncate()


inports = [{'name': 'data', 'type': 'message', "description": "Input data"}]
outports = [{'name': 'log', 'type': 'string', "description": "Logging data"}, \
            {'name': 'msg', 'type': 'message', "description": "msg with sql statement"}]

#api.set_port_callback(inports[0]['name'], process)

def test_operator():
    #api.config.package_size = 100
    msg = api.Message(attributes={'packageid':4711,'table_name':'repl_table','schema_name':'schema',\
                                  'data_outcome':True},body='')
    process(msg)

    for msg in api.queue :
        print(msg.attributes)
        print(msg.body)


if __name__ == '__main__':
    test_operator()
    if True:
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

