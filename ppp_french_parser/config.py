"""Configuration module."""
import os
import json
import logging
from ppp_libmodule.config import Config as BaseConfig
from ppp_libmodule.exceptions import InvalidConfig

class Config(BaseConfig):
    __slots__ = ('class_path',)
    config_path_variable = 'PPP_FRENCHPARSER_CONFIG'
    
    def parse_config(self, data):
        self.class_path = data['class_path']

