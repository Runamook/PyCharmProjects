import logging


def create_logger(log_filename, instance_name):
    logger = logging.getLogger(instance_name)
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    fh = logging.FileHandler(filename=log_filename)
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger