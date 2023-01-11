# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.
import os
import re
from datetime import timedelta

from ascend_fd.status import InnerError
from ascend_fd.pkg.kg_parse.utils import misc


class PathStdVariablePattern(object):
    _VAR_PATTERN_DEFS = {
        'date': {
            'pattern': '(?:[12][90])?[0-9][0-9][-._]?[01]?[0-9][-._]?[0-3]?[0-9]',
            'subvars': '((?:[12][90])?[0-9][0-9])[-._]?([01]?[0-9])[-._]?([0-3]?[0-9])',
            'type': 'datetime',
            'convert': 'Date(int($0), int($1), int($2))',
        },
        'time': {
            'pattern': '[0-2][0-9][-._:]?[0-5][0-9][-._:]?[0-5][0-9]',
            'subvars': '([0-2][0-9])[-._:]?([0-5][0-9])[-._:]?([0-5][0-9])',
            'type': 'datetime',
            'convert': 'Time(int($0), int($1), int($2))',
        },
        'datetime': {
            'pattern': '(?:[12][90])?[0-9][0-9][-._]?[01]?[0-9][-._]?[0-3]?[0-9][-_. T]?'
                       '[0-2][0-9][-._:]?[0-5][0-9][-._:]?[0-5][0-9]',
            'subvars': '((?:[12][90])?[0-9][0-9])[-._]?([01]?[0-9])[-._]?([0-3]?[0-9])[-_. T]?'
                       '([0-2][0-9])[-._:]?([0-5][0-9])[-._:]?([0-5][0-9])',
            'type': 'datetime',
            'convert': 'DateTime(int($0), int($1), int($2), int($3), int($4), int($5))',
        },
        'sn': {
            'pattern': '[0-9]+',
            'subvars': '([0-9]+)',
            'type': 'int10',
            'convert': 'int($0)',
        },
        'hex_id': {
            'pattern': '(?:0?[xX])?[0-9a-fA-F]+[hH]?',
            'subvars': '(?:0?[xX])?([0-9a-fA-F]+)[hH]?',
            'type': 'int16',
            'convert': 'int($0, 16)',
        },
        'oct_id': {
            'pattern': '(?:0?[oO])?[0-7]+[oO]?',
            'subvars': '(?:0?[oO])?([0-7]+)[oO]?',
            'type': 'int8',
            'convert': 'int($0, 8)',
        },
        'any': {
            'pattern': r'[-_\(\)\{\}\[\]<>\|#., \w]*',
            'subvars': r'([-_\(\)\{\}\[\]<>\|#., \w]*)',
            'type': 'str',
            'convert': 'str($0)'
        },
        'text': {
            'pattern': r'[-_\(\)\{\}\[\]<>\|#., \w]*',
            'subvars': r'([-_\(\)\{\}\[\]<>\|#., \w]*)',
            'type': 'str',
            'convert': 'str($0)'
        },
        'word': {
            'pattern': r'\w*',
            'subvars': r'(\w*)',
            'type': 'str',
            'convert': 'str($0)'
        },
    }
    PATTERN_STRING_TEMPLATE = \
        r"(\$\((%s)(?:<([\w]*)>)?(?::((?:-?\d+[fdhm])|(?:[<>=!\(\)\{\}\[\],' \w]*@[<>=!\(\)\{\}\[\],' \w]*)))?\))"
    PATTERN_STRING = PATTERN_STRING_TEMPLATE % "|".join(_VAR_PATTERN_DEFS.keys())
    PATTERN_REGEX = re.compile(PATTERN_STRING)
    COND_ORDER_REGEX = re.compile(r'(-?\d+)([fdhm])')
    CONVERT_REGEX = re.compile(r"\$(\d+)")

    def __init__(self, pattern_tuple):
        super(PathStdVariablePattern, self).__init__()
        self.var_ident = pattern_tuple
        if pattern_tuple[1] not in PathStdVariablePattern._VAR_PATTERN_DEFS:
            raise InnerError("not supported standard variable type '%s'" % pattern_tuple[1])
        self.type = pattern_tuple[1]
        self.data_type = PathStdVariablePattern._VAR_PATTERN_DEFS[self.type]["type"]
        self.var_name = pattern_tuple[2].strip()
        if len(self.var_name) == 0:
            self.var_name = self.var_ident
        self.condition = self.parse_condition(pattern_tuple[3].strip()) if len(pattern_tuple[3]) > 0 else None
        self.pattern = PathStdVariablePattern._VAR_PATTERN_DEFS[self.type]['pattern']
        self.subvars = PathStdVariablePattern._VAR_PATTERN_DEFS[self.type]['subvars']
        self.subvars_regex = re.compile("(%s)" % self.subvars)
        self.convert = PathStdVariablePattern.CONVERT_REGEX.sub(r'_v[\1]',
                                                                PathStdVariablePattern._VAR_PATTERN_DEFS[self.type][
                                                                    'convert'])

    @staticmethod
    def parse_condition(cond_str):
        if '@' in cond_str:
            _type = 'expr'
        else:
            _type = 'order'
        if _type == 'order':
            _res = PathStdVariablePattern.COND_ORDER_REGEX.findall(cond_str)
            if len(_res) == 0:
                raise InnerError("can not find correct condition in '%s'" % cond_str)
            _cond = (int(_res[0][0]), _res[0][1])
        elif _type == 'expr':
            _cond = cond_str.replace('@', '_v')
        else:
            raise InnerError("unsupported type '%s'" % _type)
        return _type, _cond

    def get_value(self, var_str):
        _v = self.subvars_regex.findall(var_str)
        if not _v:
            empty_str = ""
            return empty_str
        _v = _v[0][1:]
        return eval(self.convert)

    def _filter_order(self, path_vars, key):
        path_vars.sort(key=key)
        _type, _cond = self.condition
        _order, _base = _cond
        if _order < 0:
            path_vars.reverse()
            _stop = -_order
        else:
            _stop = _order
        if _base == 'f':
            return path_vars[:_stop]
        elif _base in {'d', 'h', 'm'} and self.data_type == 'datetime':
            if _base == 'd':
                _td = timedelta(days=_order)
            elif _base == 'h':
                _td = timedelta(hours=_order)
            elif _base == 'm':
                _td = timedelta(minutes=_order)
            else:
                raise InnerError("unsupported measurement '%s'" % _base)
            if _order > 0:
                _lower = key(path_vars[0])
                _upper = _lower + _td
            else:
                _upper = key(path_vars[0])
                _lower = _upper + _td
            ret_list = list()
            for item in path_vars:
                if _lower <= key(item) <= _upper:
                    ret_list.append(item)
            return ret_list
        empty_list = []
        return empty_list

    def _filter_expr(self, path_vars, key):
        _res = list()
        _type, _cond = self.condition
        for item in path_vars:
            _v = key(item)
            if eval(_cond):
                _res.append(item)
        return _res

    def filter(self, path_vars, key):
        if self.condition is None:
            return path_vars
        if self.condition[0] == 'order':
            return self._filter_order(path_vars, key)
        elif self.condition[0] == 'expr':
            return self._filter_expr(path_vars, key)
        else:
            raise InnerError("unsupported condition type '%s'" % self.condition[0])


class PathStdVariableRegex(object):
    def __init__(self, var_regex_part):
        self.var_list = list()
        var_list = PathStdVariablePattern.PATTERN_REGEX.findall(var_regex_part)
        for item in var_list:
            self.var_list.append(PathStdVariablePattern(item))
        _regex_str = var_regex_part.replace('.', r'\.').replace('+', r'\+').replace('*', '.*')
        _var_regex_str = var_regex_part.replace('.', r'\.').replace('+', r'\+').replace('*', '.*')
        for var_pattern in self.var_list:
            if not isinstance(var_pattern, PathStdVariablePattern):
                raise InnerError("the instance of var_pattern is not PathStdVariablePattern.")
            _regex_str = _regex_str.replace(var_pattern.var_ident, var_pattern.pattern)
            _var_regex_str = _var_regex_str.replace(var_pattern.var_ident, "(%s)" % var_pattern.pattern)
        self.regex_str = _regex_str
        self.var_regex_str = "(%s)" % _var_regex_str
        self.regex = re.compile(self.regex_str)
        self.var_regex = re.compile(self.var_regex_str)

    def __str__(self):
        return self.regex_str

    def __getitem__(self, item):
        if not isinstance(item, int):
            raise InnerError("the instance of item is not int.")
        return self.var_list[item]

    def get_var_patterns(self, var_with_condition_only=False):
        _res = list()
        for idx, var_pattern in enumerate(self.var_list):
            if var_pattern.condition is None and var_with_condition_only:
                continue
            _res.append((idx, var_pattern))
        return _res

    def get_var_str(self, data_str):
        _res = self.var_regex.findall(data_str)
        if len(_res) == 0:
            return []
        else:
            if isinstance(_res[0], tuple):
                return _res[0][1:]
            elif isinstance(_res[0], str):
                return []
            else:
                raise InnerError("invalid type")

    def get_var_values(self, data_str, with_name=False, named_vars_only=False):
        _val_str = self.get_var_str(data_str)
        if with_name:
            _values = dict()
            for _sn, _var in enumerate(_val_str):
                _std_var = self.var_list[_sn]
                if named_vars_only and _std_var.var_name.startswith('$'):
                    continue
                _values[_std_var.var_name] = _std_var.get_value(_var)
            return _values

        _value_list = list()
        for _sn, _var in enumerate(_val_str):
            _value_list.append(self.var_list[_sn].get_value(_var))
        return _value_list


class PathPatternRegex(object):
    _ARCHIVE_SUFFIX = ['.tar.gz', '.tar.bz2', '.bz2', '.tgz', '.gz', '.zip', '.rar', '.7z']
    _CONFLIC_SOLVE_SUFFIX = "_new"

    def __init__(self, pattern_str, sep=None):
        if os.sep == '/':
            self.sep = '/'
        elif os.sep == '\\':
            self.sep = '\\\\'
        else:
            raise InnerError("invalid path sep '%s'" % os.sep)
        if sep is not None:
            self.sep = sep
        if not pattern_str.startswith(self.sep):
            self.pattern_str = self.sep + pattern_str
        else:
            self.pattern_str = pattern_str
        self._std_patterns = self._make_std_path_patterns(self.pattern_str)
        self.regex_str = "(%s)" % self._make_regex(self._std_patterns)
        self.regex = re.compile(self.regex_str)
        self._stdvars = list()
        self._cond_stdvars = list()
        self._register_std_vars()

    def _register_std_vars(self):
        for _sn, _p in enumerate(self._std_patterns):
            _attr, _pattern = _p
            if 'stdvar' in _attr:
                if not isinstance(_pattern, PathStdVariableRegex):
                    raise InnerError("the instance of _pattern is not PathStdVariableRegex.")
                self._stdvars.extend([(_sn, _idx) for _idx, _def in _pattern.get_var_patterns()])
                self._cond_stdvars.extend(
                    [(_sn, _idx) for _idx, _def in _pattern.get_var_patterns(var_with_condition_only=True)])

    def _make_regex(self, std_patterns):
        parts = list()
        for _types, _pattern in std_patterns:
            if "path" in _types:
                parts.append('(%s)' % _pattern)
            elif "archive" in _types:
                parts.append('((?:%s(?:%s)?)(?:%s%s(?:%s)?)?)' % (
                            _pattern, PathPatternRegex._CONFLIC_SOLVE_SUFFIX, self.sep, _pattern,
                            PathPatternRegex._CONFLIC_SOLVE_SUFFIX))
            else:
                parts.append("(%s)" % _pattern)
        return self.sep.join(parts)

    @staticmethod
    def _strip_archive_suffix(path_part):
        for sfx in PathPatternRegex._ARCHIVE_SUFFIX:
            if path_part.endswith(sfx):
                return True, path_part[:-len(sfx)]
        return False, path_part

    def _make_std_path_pattern_part(self, path_part, keep_archive=False):
        if path_part.endswith(os.sep):
            empty_set = set()
            empty_str = ""
            return empty_set, empty_str
        _attr = set()
        _attr.add('path')
        _stripped, _p = self._strip_archive_suffix(path_part)
        if _stripped and not keep_archive:
            _attr.add('archive')
            _attr.discard('path')
        if '*' == _p:
            _attr.add('wildcard')
            _attr.discard('path')
            _p = _p.replace('.', r'\.').replace('+', r'\+').replace('*', '.+')
            return _attr, _p
        elif '*' in _p:
            _attr.add('partial_wildcard')
            _attr.discard('path')
        if '$(' in _p:
            _attr.add('stdvar')
            _attr.discard('path')
            _p = PathStdVariableRegex(_p)
        return _attr, _p

    def _make_std_path_patterns(self, path_pattern_str):
        parts = misc.split_all_path(path_pattern_str)
        std_parts = list()
        _last_idx = len(parts) - 1
        for _idx, item in enumerate(parts):
            if _idx != _last_idx:
                _type, _p = self._make_std_path_pattern_part(item)
            elif _idx == _last_idx:
                _type, _p = self._make_std_path_pattern_part(item, keep_archive=True)
            else:
                raise InnerError("iteration error")
            if _type is None:
                continue
            else:
                std_parts.append((_type, _p))
        return std_parts

    def match(self, path_str, with_idx=True):
        _res = list()
        _input = list()
        _ids = list()
        if isinstance(path_str, list):
            _input.extend(path_str)
        elif isinstance(path_str, str):
            _input.append(path_str)
        elif isinstance(path_str, tuple) and isinstance(path_str[0], str):
            _input.extend(path_str)
        else:
            raise InnerError("invalid format of input argument")
        for _sn, _path in enumerate(_input):
            _ret = self.regex.findall(_path)
            if len(_ret) > 0:
                _res.append(_ret[0])
                _ids.append(_sn)
        if with_idx:
            return _res, _ids
        else:
            return _res

    def match_for_vars(self, path_str, cond_vars_only=False, with_idx=True, with_name=False, named_vars_only=False):
        _matched_lines, _matched_indexes = self.match(path_str)
        _res = list()
        for _line in _matched_lines:
            _parts = _line[1:]
            _with_name_values = dict()
            _not_with_name_values = list()
            if with_name:
                if not named_vars_only:
                    _with_name_values["$(_matched_subpath)"] = _line[0]
            else:
                _not_with_name_values.append(_line[0])
            if cond_vars_only:
                var_list = self._cond_stdvars
            else:
                var_list = self._stdvars
            for _part_id, _var_id in var_list:
                _name, _pattern = self._std_patterns[_part_id]
                if not isinstance(_pattern, PathStdVariableRegex):
                    raise InnerError("the instance of _pattern is not PathStdVariableRegex.")
                if with_name:
                    _with_name_values.update(_pattern.get_var_values(_parts[_part_id], with_name, named_vars_only))
                else:
                    _not_with_name_values.append(_pattern.get_var_values(_parts[_part_id])[_var_id])
            if with_name:
                _res.append(_with_name_values)
            else:
                _res.append(tuple(_not_with_name_values))
        if with_idx:
            return _res, _matched_indexes
        else:
            return _res

    def filter(self, path_items, path_key=lambda x: x, with_idx=True):
        _path_list = [path_key(_item) for _item in path_items]
        _matched_lines, _matched_indexes = self.match_for_vars(_path_list, cond_vars_only=True)
        _candidates = list(zip(_matched_indexes, _matched_lines))
        _offset = 1
        _candidate_id_set = set(_matched_indexes)
        for _part_id, _var_id in self._cond_stdvars:
            _part_pattern_name, _part_pattern = self._std_patterns[_part_id]
            if not isinstance(_part_pattern, PathStdVariableRegex):
                raise InnerError("the instance of _part_pattern is not PathStdVariableRegex.")
            _stdvar_pattern = _part_pattern[_var_id]
            if not isinstance(_stdvar_pattern, PathStdVariablePattern):
                raise InnerError("the instance of _stdvar_pattern is not PathStdVariablePattern.")
            offset_val = _offset
            _ret = _stdvar_pattern.filter(_candidates, key=lambda x: x[1][offset_val])
            _candidate_id_set &= set([x[0] for x in _ret])
            _offset += 1
        _result_id_list = list(_candidate_id_set)
        _result_id_list.sort()
        _result = [path_items[x] for x in _result_id_list]
        if with_idx:
            return _result, _result_id_list
        else:
            return _result


class PathFilter(object):
    """path filter class"""

    def __init__(self, white_list=None, black_list=None, allow_white_list_only=False):
        super(PathFilter, self).__init__()
        self.path_patterns = list()
        if white_list is None:
            self._white_list = set()
        else:
            self._white_list = white_list
        if black_list is None:
            self._black_list = set()
        else:
            self._black_list = black_list
        self._allow_white_list_only = allow_white_list_only

    def add_path_pattern(self, pattern_str, sep=None):
        if isinstance(pattern_str, str):
            _p = PathPatternRegex(pattern_str, sep=sep)
            self.path_patterns.append(_p)
        elif isinstance(pattern_str, list):
            for _line in pattern_str:
                _p = PathPatternRegex(_line, sep=sep)
                self.path_patterns.append(_p)
        else:
            raise InnerError("incorrect format of input, only 'string' or 'list' of strings accepted.")

    def filter_path(self, path, path_key=lambda x: x):
        """filter the path"""
        the_path = os.path.abspath(path_key(path))
        for item in self._white_list:
            if item in the_path:
                return True
        if self._allow_white_list_only:
            return False
        else:
            for item in self._black_list:
                if item in the_path:
                    return False
            return True

    def filter(self, path_items, path_key=lambda x: x, with_idx=False):
        """
        Filters a set of paths.
        Returns the path that meets the PathPattern and blacklist/whitelist rules added to PathFilter.
        """
        _res_set = set()
        for _ppregex in self.path_patterns:
            _res, _ids = _ppregex.filter(path_items, path_key=path_key, with_idx=True)
            _res_set.update(_ids)
        _res_id_list = list(_res_set)
        _res_id_list.sort()
        _filtered_res_id_list = list()
        _filtered_res = list()
        for _res_id in _res_id_list:
            if self.filter_path(path_items[_res_id], path_key):
                _filtered_res_id_list.append(_res_id)
                _filtered_res.append(path_items[_res_id])
        if with_idx:
            return _filtered_res, _filtered_res_id_list
        else:
            return _filtered_res
