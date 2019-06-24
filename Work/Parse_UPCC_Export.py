import pandas as pd
import os
from os.path import join
import logging
from datetime import datetime
import sys

# TODO: Quota management
# TODO: Fix file not fond error
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
    columns = ['userid', 'service_id', 'subscription_date', 'expiry_date', 'quota_id', 'initial', 'balance', 'consumption', 'service_package_id']
    used_columns = [0, 13, 16, 18, 20, 21, 22, 23, 38]
    converters = {'subscription_date': str, 'expiry_date': str}

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


def create_subscriber_list(db_export_files, service_list):
    """
    Looks for subscribers in db_export_files list, 
    which have services defined in service_list list
    
    """

    results = {}
    
    for service_id, is_service in service_list:
        intermediate_results = []
        for db_file in db_export_files:
            subscriber_list = find_subscribers_by_service(service_id, is_service, db_file)
            
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
        logging.info(u'Something happened %s', e)
        if e.errno != 'errno.ENOENT':
            raise
        else:
            pass

        '''
          File "/home/egk/Scripts/Hua/Parse_UPCC_Export.py", line 98, in silent_remove
          os.remove(filename)
          FileNotFoundError: [Errno 2] No such file or directory: '1494_rmv.txt'
        '''

    return


class SubscriberList(object):
    def __init__(self, subscriber_list):
        self.subscriber_list = subscriber_list

    def resubscribe_service_mml(self):
        """
        Read a dict 
            {
            (service_tuple):[[(msisdn,date), (msisdn,date)...],[...]],
            (service_tuple):[[(msisdn,date), (msisdn,date)...],[...]]
            }
        Generates a list of MML commands to remove and add services
        
        """
        
        for (service_id, is_service), msisdn_list_of_lists in self.subscriber_list.items():
            
            if is_service:
                
                add_filename = '%s_add.txt' % service_id
                rmv_filename = '%s_rmv.txt' % service_id
                
                silent_remove(add_filename)
                silent_remove(rmv_filename)
                
                logging.info(u'Processing service %s', service_id)
    
                add_extra_args = '\
                SRVUSAGESTATE=Normal, \
                SRVROAMINGTYPE=NULL, \
                SRVCONTACTMETHOD=None, \
                SRVCREATESUBSCRIBER=No, \
                PAYMENTFLAG=Yes, \
                SRVEXATTR1=255;'

                rmv_extra_args = '\
                TERMIND=Immediate termination, \
                SRVDELETESUBSCRIBER=No;'
                
                for msisdn_list in msisdn_list_of_lists:
                    
                    for (msisdn, subscription_date) in msisdn_list:
                        
                        _subscription_date = datetime.strptime(subscription_date, '%Y%m%d%H%M%S')
                        subscription_date_h = _subscription_date.strftime('%Y&%m&%d&%H&%M&%S')
                    
                        ADD_PSRV_CMD = 'ADD PSRV: \
                        USRIDENTIFIER="%s", \
                        SRVNAME="%s", \
                        SRVSUBSCRIBEDATE=%s, \
                        SRVSTARTDATETIME=%s, \
                        %s\n' % (msisdn, service_id, subscription_date_h, subscription_date_h, add_extra_args)
                        RMV_PSRV_CMD = 'RMV PSRV: \
                        USRIDENTIFIER="%s", \
                        SRVNAME="%s", %s\n' % (msisdn, service_id, rmv_extra_args)
                        
                        with open(add_filename, 'a') as add_file: 
                            add_file.write(ADD_PSRV_CMD)    
    
                        with open(rmv_filename, 'a') as rmv_file:
                            rmv_file.write(RMV_PSRV_CMD)
                    
            elif not is_service:
                
                logging.info(u'Processing service Package %s', service_id)
                
                sys.exit('Please complete the program first!')
                
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
                         
               ADD PSRVPKG: USRIDENTIFIER="msisdn", 
                            SRVPKGNAME="service_id", 
                            SRVPKGSUBSCRIBEDATE=2018&10&24&12&09&40, 
                            SRVPKGSTARTDATETIME=2018&10&24&12&09&41, 
                            SRVPKGROAMINGTYPE=NULL, 
                            SRVPKGCONTACTMETHOD=None;
            
               RMV PSRVPKG: USRIDENTIFIER="msisdn",
                            SRVPKGNAME="service_id", 
                            TERMIND=Immediate termination;
            
            '''
    def create_mml_fix_date(self):
        """
        Read a dict 
            {
            (service_tuple):[[(msisdn,start_date,expiry_date), (msisdn,start_date,expiry_date)...],[...]],
            (service_tuple):[[(msisdn,start_date,expiry_date), (msisdn,start_date,expiry_date)...],[...]]
            }
        Generates a list of MML commands to modify expiry date
        
        """
        for (service_id, is_service), msisdn_list_of_lists in self.subscriber_list.items():

            if is_service:
                raise NotImplementedError
        raise NotImplementedError
    
    
def meta():
    
    root_directory = '/home/egk/Pile/P3/DB_Export'
    directory = root_directory + '/Files'
    
    os.chdir(root_directory)

    service_list = [('1485', True)]

    # service_list = [
    #    ( '1494', True ),
    #    ( '1493', True ),
    #    ( '1486', True )
    #    ]

    logging.info(service_list)
    logging.info(u'Working directory %s', directory)
    
    db_export_files = get_export_files(directory)
    subscriber_list = create_subscriber_list(db_export_files, service_list)
    # create_mml(subscriber_list)
    pcrf_subscriber_list = SubscriberList(subscriber_list)
    pcrf_subscriber_list.create_mml_fix_date()
    
    
if __name__ == '__main__':

    logging.basicConfig(
            format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
            level=logging.INFO)
    
    meta()
