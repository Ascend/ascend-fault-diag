# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2023. All rights reserved.
class BaseError(Exception):
    code = 500
    description = "Internal Server Error."

    def __init__(self, description=None):
        if description:
            self.description = description
        super().__init__(description)

    def __str__(self):
        return f"{self.__class__.__name__}({self.code}): {self.description}"


class PathError(BaseError):
    code = 501
    description = "Invalid Path."


class FileNotExistError(BaseError):
    code = 502
    description = "File not exist."


class JavaError(BaseError):
    code = 503
    description = "Java program not found."


class InfoNotFoundError(BaseError):
    code = 504
    description = "Information not found."


class InfoIncorrectError(BaseError):
    code = 505
    description = "Information not correct."


class FileOpenError(BaseError):
    code = 506
    description = "Open file failed."


class InnerError(BaseError):
    code = 507
    description = "Inner error, please check detail log."


class ParamError(BaseError):
    code = 508
    description = "ParamError."


class SuccessRet:
    code = 200
    description = "Successful operation."
