import pandas as pd
import os
from os.path import join
import logging
import datetime as dt
import sys


# TODO: Quota management
# TODO: Make filecount check - if 0 - do not continue
# TODO: Class

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
    columns = ['userid', 'service_id', 'subscription_date', 'expiry_date', 'quota_id', 'service_package_id']
    used_columns = [0, 13, 16, 18, 20, 38]

    df = pd.read_csv(db_file, usecols=used_columns, names = columns)
    df = df.fillna('Not_Found')
    
    if is_service:
        sel1 = df['service_id'].str.contains(service)   # Change to exact match!!!
        # sel1 = df['service_id'].str.match(service)   # Change to exact match!!!
    
    elif not is_service:
        sel1 = df['service_package_id'].str.contains(service)
        # sel1 = df['service_package_id'].str.match(service)
    
    subscriber_list = []
    
    for index, row in df[sel1].iterrows():

        subscriber = (row['userid'], row['subscription_date'], row['expiry_date'])
        
        subscriber_list.append(subscriber)
    
    return subscriber_list


def create_subscriber_list(db_export_files, service_list, directory):
    """
    Looks for subscribers in db_export_files list, 
    which have services defined in service_list list
    
    """

    results = {}
    
    for service_id, is_service in service_list:
        intermediate_results = []
        for db_file in db_export_files:
            subscriber_list = find_subscribers_by_service(service_id, 
                                                             is_service, 
                                                             db_file)
            
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
    except FileNotFoundError:
        logging.info(u'File %s not found', filename)

        """
          File "/home/egk/Scripts/Hua/Parse_UPCC_Export.py", line 98, in silent_remove
          os.remove(filename)
          FileNotFoundError: [Errno 2] No such file or directory: '1494_rmv.txt'
        """

    return


def increment_by_month(parsed_subscription_date):
    if parsed_subscription_date.strftime('%m') == '11':
        # Subscribed in November
        return parsed_subscription_date + dt.timedelta(days=30)
    if parsed_subscription_date.strftime('%m') == '12':
        # Subscribed in December
        return parsed_subscription_date + dt.timedelta(days=31)
    
    
def create_mml2(subscriber_list):
    """
    Reads a dict
        {
        (service_tuple):[[(msisdn,date,date), (msisdn,date,date)...],[...]],
        (service_tuple):[[(msisdn,date,date), (msisdn,date,date)...],[...]]
        }
    Generates a list of MML commands to remove and add services
    
    a = {1:'11', 2:'22', 3:'33'}
    for i, j in a.items():
        print(i, j)
    1 11
    2 22
    3 33
    """
    
    for (service_id, is_service), msisdn_list_of_lists in subscriber_list.items():
        
        if is_service:
            
            mod_filename = '%s_mod.txt' % service_id
            log_filename = '%s_mod.log' % service_id

            silent_remove(mod_filename)
            silent_remove(log_filename)
            
            
            logging.info(u'Processing service %s', service_id)

            # MOD PSRV: USRIDENTIFIER="79800880871", SRVNAME="1332", SRVENDDATETIME=2019&01&17&14&07&05, SRVEXATTR1=255;
            
            for msisdn_list in msisdn_list_of_lists:
                
                for (msisdn, subscription_date, expiry_date) in msisdn_list:
                    
                    if expiry_date == 'FFFFFFFFFFFFFF':
                        # Wut?!
                        logging.debug(u'%s expiry date: %s', msisdn, expiry_date)
                        log_string = '%s expiry date: %s\n' % (msisdn, expiry_date)
                        with open(log_filename, 'a') as log_file:
                            log_file.write(log_string) 
                        continue
                        
                        
                    parsed_expiry_date = dt.datetime.strptime(expiry_date, '%Y%m%d%H%M%S')
                    
                    if parsed_expiry_date.strftime('%H%M%S') == '000000':
                        # Provisioning error, fixing
                        
                        if subscription_date == 'FFFFFFFFFFFFFF':
                            logging.info(u'%s subscription date: %s', msisdn, subscription_date)
                            log_string = '%s subscription date: %s\n' % (msisdn, subscription_date)
                            with open(log_filename, 'a') as log_file:
                                log_file.write(log_string)                            
                            continue
                        
                        try:
                            # Parse pandas subscription date
                            # Can be 20181214091551.0 or 20190118132342
                            new_subscription_date = str(int(subscription_date))
                        except ValueError:
                            new_subscription_date = subscription_date.split('.')[0]
                            logging.info(u'Fixing subscipption date %s to %s', subscription_date, new_subscription_date)
                            
                        parsed_subscription_date = dt.datetime.strptime(new_subscription_date, '%Y%m%d%H%M%S')
                        expiry_date = increment_by_month(parsed_subscription_date)
                        # Convert parsed date to UPCC MML format
                        upcc_expiry_date = expiry_date.strftime('%Y&%m&%d&%H&%M&%S')

                        MOD_PSRV_CMD = 'MOD PSRV: USRIDENTIFIER="%s", SRVNAME="%s", SRVENDDATETIME=%s, SRVEXATTR1=255;\n' % (msisdn, service_id, upcc_expiry_date)
                        
                        with open(mod_filename, 'a') as mod_file: 
                            mod_file.write(MOD_PSRV_CMD)    
    
                    else:
                        logging.info(u'Not fixing %s ExpDate %s', msisdn, parsed_expiry_date.strftime('%Y%m%d%H%M%S'))

              
def meta():
    
    root_directory = '/home/egk/Pile/P3/DB_Export'
    directory = root_directory + '/Files'
    
    os.chdir(root_directory)

    service_list = [('1485', True)]
    # service_list = [
    #    ( '1332', True )
    #    ]

    logging.info(service_list)
    logging.info(u'Working directory %s', directory)
    
    db_export_files = get_export_files(directory)
    subscriber_list = create_subscriber_list(db_export_files, service_list, directory)
    create_mml2(subscriber_list)


if __name__ == '__main__':

    logging.basicConfig(
            format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
            level=logging.INFO)
    
    meta()
