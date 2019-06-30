import pandas as pd
import os
from os.path import join
import logging
from datetime import datetime
import sys

# TODO: Quota management
# TODO: Make filecount check - if 0 - do not continue


def get_export_files(directory):
    """
    Return a list of UPCC export files from given directory
    
    """
    db_export_files = []
    for root, folders, files in os.walk(directory):
        for f in files:
            
            if f[-3:] == 'txt':
                logging.info(u'Found %s', f)
                db_export_files.append(join(root,f))
            else:
                logging.info(u'Scipping %s', f)
 
    logging.info(u'Found %s txt files', len(db_export_files))
    return db_export_files


def find_subscribers_by_service(service, is_service, db_file):
    """
    
    
    """
    # used_columns=[0, 1, 13,38, 20]
    # columns = ['userid', 'msisdn', 'service_id', 'quota_id', 'service_package_id']
    columns = [
        'userid',
        'service_id',
        'subscription_date',
        'expiry_date',
        'quota_id',
        'initial',
        'balance',
        'consumption',
        'service_package_id'
    ]
    used_columns = [
        0,
        13,
        16,
        18,
        20,
        21,
        22,
        23,
        38
    ]

    converters = {'userid': str,
                  'subscription_date': str,
                  'expiry_date': str,
                  'service_package_id': str,
                  'quota_id': str,
                  'initial': str,
                  'balance': str,
                  'consumption': str}

    df = pd.read_csv(db_file, usecols=used_columns, names=columns, converters=converters)
    df = df.fillna('Not_Found')
    logging.info(f"Parsing file {db_file}")

    subscriber_list = []

    if is_service:
        sel1 = df['service_id'].str.contains(service)   # Change to exact match!!!
        df = df[sel1]
        # sel1 = df['service_id'].str.match(service)   # Change to exact match!!!

        for index, row in df.iterrows():
            subscriber = (
                row['userid'],
                row['subscription_date'],
                "quota_placeholder",
                "initial_placeholder",
                "balance_placeholder",
                "consumption_placeholder"
            )
            logging.debug(f"Service: {service}, subscriber: {subscriber}")

            subscriber_list.append(subscriber)

    elif not is_service:
        df = df[(df.service_package_id == service) & (df.quota_id.str.contains(service))]

        for index, row in df.iterrows():

            subscriber = (
                row['userid'],
                row['subscription_date'],
                row['quota_id'],
                row['initial'],
                row['balance'],
                row['consumption']
                )
            logging.debug(f"Service: {service}, subscriber: {subscriber}")
            subscriber_list.append(subscriber)
    
    return subscriber_list


def create_subscriber_list(db_export_files, service_list, directory):
    """
    Looks for subscribers in db_export_files list, 
    which have services defined in service_list list
    
    """
    results = {}
    
    for service_id, is_service in service_list:
        logging.info(f"Looking for {service_id} is service = {is_service}")

        intermediate_results = []
        for db_file in db_export_files:
            subscriber_list = find_subscribers_by_service(
                service_id,
                is_service,
                db_file
            )
            
            logging.info(u'%s subscribers with service %s in %s',
                         len(subscriber_list), 
                         service_id,
                         db_file)
            
            intermediate_results.append(subscriber_list)

        results[(service_id, is_service)] = intermediate_results

    return results


def silent_remove(filename):
                
    try:
        logging.info(u'Trying to remove %s', filename)
        os.remove(filename)
    except FileNotFoundError as e:
        logging.info(u'No such file %s', e)

        """
          File "/home/egk/Scripts/Hua/Parse_UPCC_Export.py", line 98, in silent_remove
          os.remove(filename)
          FileNotFoundError: [Errno 2] No such file or directory: '1494_rmv.txt'
        """

    return


def get_mml_date(date_str):
    _subscription_date = datetime.strptime(date_str, '%Y%m%d%H%M%S')
    subscription_date_h = _subscription_date.strftime('%Y&%m&%d&%H&%M&%S')
    return subscription_date_h


def create_mml(subscriber_list):
    """
    Read a dict 
        {
        (service_tuple):[[(msisdn,date,quota,init,balance,consumption), (msisdn,date,quota,init,balance,consumption)...],[...]],
        (service_tuple):[[(msisdn,date,quota,init,balance,consumption), (msisdn,date,quota,init,balance,consumption)...],[...]]
        }
    Generates a list of MML commands to remove and add services
    
    """
    for (service_id, is_service), msisdn_list_of_lists in subscriber_list.items():
        
        if is_service:
            
            add_filename = '%s_add.txt' % service_id
            rmv_filename = '%s_rmv.txt' % service_id
            
            silent_remove(add_filename)
            silent_remove(rmv_filename)
            
            logging.info(u'Creating MML file for service %s', service_id)

            add_extra_args = 'SRVUSAGESTATE=Normal, SRVROAMINGTYPE=NULL, SRVCONTACTMETHOD=None, SRVCREATESUBSCRIBER=No, PAYMENTFLAG=Yes, SRVEXATTR1=255;'
            rmv_extra_args = 'TERMIND=Immediate termination, SRVDELETESUBSCRIBER=No;'

            for msisdn_list in msisdn_list_of_lists:
                
                for (msisdn, subscription_date, quota_id, initial, balance, consumption) in msisdn_list:
                    
                    subscription_date_h = get_mml_date(subscription_date)
                
                    ADD_PSRV_CMD = 'ADD PSRV: USRIDENTIFIER="%s", SRVNAME="%s", SRVSUBSCRIBEDATE=%s, SRVSTARTDATETIME=%s, %s\n' % (msisdn, service_id, subscription_date_h, subscription_date_h, add_extra_args)
                    RMV_PSRV_CMD = 'RMV PSRV: USRIDENTIFIER="%s", SRVNAME="%s", %s\n' % (msisdn, service_id, rmv_extra_args)
                    
                    with open(add_filename, 'a') as add_file: 
                        add_file.write(ADD_PSRV_CMD)    

                    with open(rmv_filename, 'a') as rmv_file:
                        rmv_file.write(RMV_PSRV_CMD)

                    '''ADD PSRV: USRIDENTIFIER="msisdn", 
                                 SRVNAME="service_id", 
                                 SRVSUBSCRIBEDATE=2018&10&24&12&07&47, 
                                 SRVSTARTDATETIME=2018&10&24&12&07&52, 
                                 SRVUSAGESTATE=Normal, 
                                 SRVROAMINGTYPE=NULL, 
                                 SRVCONTACTMETHOD=None, 
                                 SRVCREATESUBSCRIBER=No, 
                                 PAYMENTFLAG=Yes, 
                                 SRVEXATTR1=255;
            
                       RMV PSRV: USRIDENTIFIER="msisdn", 
                                 SRVNAME="service_id", 
                                 TERMIND=Immediate termination, 
                                 SRVDELETESUBSCRIBER=No;
                    '''
        elif not is_service:

            logging.info(u'Creating MML file for service package %s', service_id)

            add_filename = '%s_pkg_add.txt' % service_id
            rmv_filename = '%s_pkg_rmv.txt' % service_id

            silent_remove(add_filename)
            silent_remove(rmv_filename)

            add_extra_args = 'SRVPKGROAMINGTYPE=NULL, SRVPKGCONTACTMETHOD=None;'
            rmv_extra_args = 'TERMIND=Immediate termination;'

            for msisdn_list in msisdn_list_of_lists:

                for (msisdn, subscription_date, quota_id, initial, balance, consumption) in msisdn_list:
                    subscription_date_h = get_mml_date(subscription_date)

                    ADD_PSRV_CMD = 'ADD PSRVPKG: USRIDENTIFIER="%s", SRVPKGNAME="%s", SRVPKGSUBSCRIBEDATE=%s, SRVPKGSTARTDATETIME=%s, %s\n' % (msisdn, service_id, subscription_date_h, subscription_date_h, add_extra_args)
                    MOD_PQUOTA_CMD = 'MOD PQUOTA: USRIDENTIFIER="%s", QTANAME="%s", QTABALANCE=%s, QTACONSUMPTION=%s, REALTIMEFLAG=False;\n' % (msisdn, quota_id, balance, consumption)
                    RMV_PSRV_CMD = 'RMV PSRVPKG: USRIDENTIFIER="%s", SRVPKGNAME="%s", %s\n' % (msisdn, service_id, rmv_extra_args)

                    with open(add_filename, 'a') as add_file:
                        add_file.write(ADD_PSRV_CMD)
                        add_file.write(MOD_PQUOTA_CMD)

                    with open(rmv_filename, 'a') as rmv_file:
                        rmv_file.write(RMV_PSRV_CMD)

                    '''
                       ADD PSRVPKG: USRIDENTIFIER="msisdn", 
                                    SRVPKGNAME="service_id", 
                                    SRVPKGSUBSCRIBEDATE=2018&10&24&12&09&40, 
                                    SRVPKGSTARTDATETIME=2018&10&24&12&09&41, 
                                    SRVPKGROAMINGTYPE=NULL, 
                                    SRVPKGCONTACTMETHOD=None;
                                    
                        MOD PQUOTA: USRIDENTIFIER="79770020073",
                                    QTANAME="q_m_default_1489", 
                                    QTABALANCE=1097152, 
                                    QTACONSUMPTION=1000000, 
                                    REALTIMEFLAG=False;
                    
                       RMV PSRVPKG: USRIDENTIFIER="msisdn",
                                    SRVPKGNAME="service_id", 
                                    TERMIND=Immediate termination;
                    '''


def meta():
    
    root_directory = '/home/egk/Pile/P3/DB_Export'
    directory = root_directory + '/Files'
    
    os.chdir(root_directory)

    # (Service/Package id, True = Service/False = Package)
    service_list = [
        ('1485', True),
        ('1489', False)
    ]
    # service_list = [
    #    ( '1494', True ),
    #    ( '1493', True ),
    #    ( '1486', True )
    #    ]

    logging.info(service_list)
    logging.info(u'Working directory %s', directory)
    
    db_export_files = get_export_files(directory)
    subscriber_list = create_subscriber_list(db_export_files, service_list, directory)
    create_mml(subscriber_list)


if __name__ == '__main__':

    logging.basicConfig(
            format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
            level=logging.DEBUG)
    
    meta()
