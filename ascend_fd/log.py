# coding: UTF-8
# Copyright (c) 2022. Huawei Technologies Co., Ltd. ALL rights reserved.
import os
import logging
import logging.handlers


LOG_WIDTH = 100
LOG_MAX_SIZE = 10 * 1024 * 1024
LOG_MAX_BACKUP_COUNT = 20
DETAIL_FORMAT = '[%(asctime)s] %(levelname)s [pid:%(process)d] [%(threadName)s] ' \
                '[%(filename)s:%(lineno)d %(funcName)s] %(message)s'
SIMPLE_FORMAT = '[%(levelname)s] > %(message)s'


class MyRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def doRollover(self):
        try:
            os.chmod(self.baseFilename, mode=0o440)
        except PermissionError:
            os.chmod(f"{self.baseFilename}.{LOG_MAX_BACKUP_COUNT}", mode=0o640)
        finally:
            logging.handlers.RotatingFileHandler.doRollover(self)
            os.chmod(self.baseFilename, mode=0o640)


def init_job_logger(output_path, log_name):
    log_path = os.path.join(output_path, "log")
    os.makedirs(log_path, 0o700, exist_ok=True)
    logging_file_path = os.path.join(log_path, f"{log_name}.log")
    file_handler = MyRotatingFileHandler(logging_file_path, maxBytes=LOG_MAX_SIZE, backupCount=LOG_MAX_BACKUP_COUNT)
    file_handler.setFormatter(logging.Formatter(DETAIL_FORMAT))

    logger = logging.getLogger(log_name)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    os.chmod(logging_file_path, 0o640)

    return logger


def init_main_logger(output_path):
    logger = init_job_logger(output_path, "ascend_fd")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(SIMPLE_FORMAT))

    logger.addHandler(stream_handler)

    return logger
