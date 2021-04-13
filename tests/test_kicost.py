#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_kicost
----------------------------------

Tests for `kicost` module.

pytest-3 --log-cli-level debug
"""

import unittest
import subprocess
import logging
import os

# Defined as True to collect real world queries
ADD_QUERY_TO_KNOWN = False


def run_test(inputs, output, extra=None, price=False):
    # Always fake the currency rates
    os.environ['KICOST_CURRENCY_RATES'] = 'tests/currency_rates.xml'
    # Now choose between recording the KitSpace queries or fake them
    if price and ADD_QUERY_TO_KNOWN:
        os.environ['KICOST_LOG_HTTP'] = 'tests/kitspace_queries.txt'
        with open('tests/kitspace_queries.txt', 'at') as f:
            if len(inputs) == 1:
                f.write('# ' + inputs[0] + '\n')
            else:
                f.write('# ' + str(inputs) + '\n')
        server = None
    else:
        os.environ['KICOST_KITSPACE_URL'] = 'http://localhost:8000'
        fo = open('tests/server_stdout.txt', 'at')
        fe = open('tests/server_stderr.txt', 'at')
        server = subprocess.Popen('./tests/dummy-web-server.py', stdout=fo, stderr=fe)
    if not os.path.isdir('tests/result_test'):
        os.mkdir('tests/result_test')
    if not os.path.isdir('tests/log_test'):
        os.mkdir('tests/log_test')
    try:
        # Run KiCost
        cmd = ['kicost', '--debug', '10']
        if not price:
            cmd.append('--no_price')
        if extra:
            cmd.extend(extra)
        out_xlsx = 'tests/' + output + '.xlsx'
        cmd.extend(['-o', out_xlsx])
        cmd.extend(['-wi'] + ['tests/' + n for n in inputs])
        logging.debug('Running '+str(cmd))
        log_err = open('tests/log_test/' + output + '_error.log', 'wt')
        log_out = open('tests/log_test/' + output + '_out.log', 'wt')
        subprocess.check_call(cmd, stderr=log_err, stdout=log_out)
        log_err.close()
        log_out.close()
        res_csv = 'tests/result_test/' + output + '.csv'
        # Convert to CSV
        logging.debug('Converting to CSV')
        cmd = ['xlsx2csv']
        if not price:
            cmd.append('--skipemptycolumns')
        cmd.append(out_xlsx)
        p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        # Filter it
        filter = r'\$ date|Prj date:.*\(file|kicost'
        if not price:
            filter += '|Total purchase'
        with open(res_csv, 'w') as f:
            p2 = subprocess.Popen(['egrep', '-i', '-v', '(' + filter + ')'], stdin=p1.stdout, stdout=f)
            p2.communicate()[0]
        # Check with diff
        ref_csv = 'tests/expected_test/' + output + '.csv'
        cmd = ['diff', '-u', ref_csv, res_csv]
        logging.debug('Running '+str(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    finally:
        # Kill the server
        if server is not None:
            server.terminate()
            fo.close()
            fe.close()
    logging.info(output+' OK')


def run_test_check(name, inputs=None, output=None, extra=None, price=False):
    logging.debug('Test name: ' + name)
    if inputs is None:
        inputs = name
    if isinstance(inputs, str):
        inputs = [inputs]
    if output is None:
        output = inputs[0]
        if output.endswith('.csv'):
            output = output[:-4]
    try:
        run_test(inputs, output, extra, price)
    except subprocess.CalledProcessError as e:
        logging.error('Failed test: ' + name)
        if e.output:
            logging.error('Output from command: ' + e.output.decode())
        raise e


def test_300_010():
    run_test_check('300-010', price=True)


def test_acquire_PWM_1():
    run_test_check('acquire-PWM', price=True)


def test_acquire_PWM_2():
    run_test_check('acquire-PWM_2', price=True)


def test_Aeronav_R():
    run_test_check('Aeronav_R', price=True)


def test_b3u():
    run_test_check('b3u_test', price=True)


def test_bbsram():
    run_test_check('bbsram', price=True)


def test_BoulderCreekMotherBoard():
    # This test doesn't have any kind of manf# or DISTRIBUTOR#
    run_test_check('BoulderCreekMotherBoard')


def test_CAN_Balancer():
    run_test_check('CAN Balancer', price=True)


def test_Decoder():
    run_test_check('Decoder', price=True)


def test_fitting():
    run_test_check('fitting_test', price=True)


def test_Indium_X2():
    run_test_check('Indium_X2', price=True)


def test_kc():
    run_test_check('kc-test', price=True)


def test_LedTest():
    run_test_check('LedTest', price=True)


def test_local_Indium_X2():
    run_test_check('local_Indium_X2', price=True)


def test_NF6X_TestBoard():
    run_test_check('NF6X_TestBoard', price=True)


def test_Receiver_1W():
    run_test_check('Receiver_1W', price=True)


def test_RPi():
    run_test_check('RPi-Test', price=True)


def test_RX_LR_lite():
    run_test_check('RX LR lite', price=True)


def test_safelink_receiver():
    run_test_check('safelink_receiver', price=True)


def test_single_component():
    run_test_check('single_component', price=True)


def test_StickIt_Hat_old():
    run_test_check('StickIt-Hat-old', price=True)


def test_StickIt_Hat_new():
    run_test_check('StickIt-Hat', price=True)


def test_StickIt_QuadDAC():
    run_test_check('StickIt-QuadDAC', price=True)


def test_StickIt_RotaryEncoder():
    # Tests an embedded price from Aliexpress
    run_test_check('StickIt-RotaryEncoder', price=True)


def test_subparts():
    run_test_check('subparts', price=True)


def test_1():
    run_test_check('test')


def test_2():
    run_test_check('test2')


def test_3():
    run_test_check('test3')


def test_Parts():
    run_test_check('TestParts')


def test_part_list_big():
    run_test_check('part_list_big.csv')


def test_part_list_small_hdr():
    run_test_check('part_list_small.csv')


def test_part_list_small_nohdr():
    run_test_check('part_list_small_nohdr.csv')


def test_multiproject_1():
    run_test_check('multiproject_1 (1 single)', 'multipart')
    run_test_check('multiproject_1 (2 single)', 'multipart2')
    run_test_check('multiproject_1', ['multipart', 'multipart2.xml'], 'multipart1+2')


def test_variants_1():
    test_name = 'variants_1'
    run_test_check(test_name, 'variants_1')
    run_test_check(test_name + '(test)', 'variants_1', 'variants_1_test', ['--variant', 'test'])
    run_test_check(test_name + '(production)', 'variants_1', 'variants_1_production', ['--variant', 'production'])
    run_test_check(test_name + '(default)', 'variants_1', 'variants_1_default', ['--variant', 'default'])


class TestKicost(unittest.TestCase):

    def setUp(self):
        pass

    def test_something(self):
        pass

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
