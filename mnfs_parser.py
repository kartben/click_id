#!/usr/bin/env python

# COPYRIGHT (c) 2019-2020 Friedt Professional Engineering Services, Inc
# Copyright (c) 2015-2016 Google, Inc.
# Copyright (c) 2015 Linaro, Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import collections
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import sys

### Exception management
class Error(Exception):
    def __init__(self, msg=''):
        self.message = msg
        super(Error, self).__init__(msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__

### Manifest internal representation

class Manifest(object):
    """
    The Manifest is the composition of a Manifest Header and a set of
    Descriptors
    """

    def __init__(self):
        self.header = None
        self.descriptors = []

        self.string_descs = {}
        self.device_descs = {}
        self.property_descs = {}
        self.interface_desc = None
        self.mikrobus_desc = None
        self.bundle_descs = {}
        self.cport_descs = {}

    def add_header(self, hdr):
        self.header = hdr

    def __add_desc(self, desc):
        self.descriptors.append(desc)

    def add_interface_desc(self, desc):
        assert self.interface_desc is None, \
                "multiple instances of '{}'".format(self.instances.title)
        self.interface_desc = desc
        self.__add_desc(desc)

    def add_mikrobus_desc(self, desc):
        self.mikrobus_desc = desc
        self.__add_desc(desc)

    def __add_desc_dict(self, dict_, desc):
        if desc.id_ in dict_:
            raise Error("duplicated 'id' for descriptors '{}' and '{}'"
                    .format(desc, dict_[desc.id_]))
        dict_[desc.id_] = desc

    def add_string_desc(self, desc):
        self.__add_desc_dict(self.string_descs, desc)
        self.__add_desc(desc)
    
    def add_property_desc(self, desc):
        self.__add_desc_dict(self.property_descs, desc)
        self.__add_desc(desc)

    def add_device_desc(self, desc):
        self.__add_desc_dict(self.device_descs, desc)
        self.__add_desc(desc)
    
    def add_bundle_desc(self, desc):
        self.__add_desc_dict(self.bundle_descs, desc)
        self.__add_desc(desc)

    def add_cport_desc(self, desc):
        self.__add_desc_dict(self.cport_descs, desc)
        self.__add_desc(desc)

    def __str__(self):
        r = "{}".format(self.header)
        r += "\n{}".format(self.interface_desc)
        if self.mikrobus_desc is not None:
            r += "\n{}".format(self.mikrobus_desc)
        if self.device_descs is not None:
            for k in sorted(self.device_descs):
                r += "\n{}".format(self.device_descs[k])
        if self.property_descs is not None:
            for k in sorted(self.property_descs):
                r += "\n{}".format(self.property_descs[k])
        for k in sorted(self.string_descs):
            r += "\n{}".format(self.string_descs[k])
        for k in sorted(self.bundle_descs):
            r += "\n{}".format(self.bundle_descs[k])
        for k in sorted(self.cport_descs):
            r += "\n{}".format(self.cport_descs[k])
        return r

class ManifestHeader(object):
    GB_VERSION_MAJOR = 0
    GB_VERSION_MINOR = 1

    def __init__(self, major, minor):
        if (major != ManifestHeader.GB_VERSION_MAJOR or
                minor != ManifestHeader.GB_VERSION_MINOR):
            raise Error("invalid '[{}]' format version '{}.{}'"
                    "(only supports '{}.{}')".format(
                        MnfsParser.MNFS_HEADER, major, minor,
                        ManifestHeader.GB_VERSION_MAJOR,
                        ManifestHeader.GB_VERSION_MINOR))
        self.major = major
        self.minor = minor

    def __str__(self):
        r = "[{}]\n".format(MnfsParser.MNFS_HEADER)
        r += "version-major = {}\n".format(self.major)
        r += "version-minor = {}\n".format(self.minor)
        return r

class Descriptor(object):
    def __init__(self, section, used = False):
        self.section = section
        self.used = used

class InterfaceDescriptor(Descriptor):
    def __init__(self, vendor_string_id, product_string_id, section):
        super(InterfaceDescriptor, self).__init__(section, True)
        self.vsid = vendor_string_id
        self.psid = product_string_id

    def __str__(self):
        r = "[{}]\n".format(MnfsParser.INTERFACE_DESC)
        r += "vendor-string-id = {:#x}\n".format(self.vsid)
        r += "product-string-id = {:#x}\n".format(self.psid)
        return r

class MikrobusDescriptor(Descriptor):
    def __init__(self, pwm, _int, rx, tx, scl, sda, mosi, miso, sck, cs, rst, an, section):
        super(MikrobusDescriptor, self).__init__(section, True)
        self.pwm = pwm
        self.int = _int
        self.rx = rx
        self.tx = tx
        self.scl = scl
        self.sda = sda
        self.mosi = mosi
        self.miso = miso
        self.sck = sck
        self.cs = cs
        self.rst = rst
        self.an = an

    def __str__(self):
        r = "[{}]\n".format(MnfsParser.MIKROBUS_DESC)
        r += "pwm-state = {:#x}\n".format(self.pwm)
        r += "int-state = {:#x}\n".format(self.int)
        r += "rx-state = {:#x}\n".format(self.rx)
        r += "tx-state = {:#x}\n".format(self.tx)
        r += "scl-state = {:#x}\n".format(self.scl)
        r += "sda-state = {:#x}\n".format(self.sda)
        r += "mosi-state = {:#x}\n".format(self.mosi)
        r += "miso-state = {:#x}\n".format(self.miso)
        r += "sck-state = {:#x}\n".format(self.sck)
        r += "cs-state = {:#x}\n".format(self.cs)
        r += "rst-state = {:#x}\n".format(self.rst)	
        r += "an-state = {:#x}\n".format(self.an)
        return r

class StringDescriptor(Descriptor):
    def __init__(self, id_, string, section):
        super(StringDescriptor, self).__init__(section)
        if id_ == 0:
            raise Error("invalid id for '[{}]' (cannot be 0)".format(section))
        self.id_ = id_
        self.string = string
        self._parent = None

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, desc):
        if self._parent is not None:
            raise Error("multiple references to [{}]".format(self.section))
        self.used = True
        self._parent = desc

    def __str__(self):
        r = ""
        if self._parent is not None:
            if self.id_ == self.parent.vsid:
                r += "; Interface vendor string\n"
            elif self.id_ == self.parent.psid:
                r += "; Interface product string\n"
        r += "[{} {:#x}]\n".format(MnfsParser.STRING_DESC, self.id_)
        r += "string = {}\n".format(self.string)
        return r

class BundleDescriptor(Descriptor):

    bundle_id = 1

    bundle_class = {
            0x00: 'Control',
            0x01: 'AP',
            0x05: 'HID',
            0x08: 'Power Supply',
            0x0a: 'Bridged PHY',
            0x0c: 'Display',
            0x0d: 'Camera',
            0x0e: 'Sensor',
            0x0f: 'Lights',
            0x10: 'Vibrator',
            0x11: 'Loopback',
            0x12: 'Audio',
            0x14: 'SVC',
            0x15: 'Firmware',
            0xfe: 'Raw',
            0xff: 'Vendor Specific',
            }

    def __init__(self, id_, class_, section):
        super(BundleDescriptor, self).__init__(section)
        if id_ == 0 and class_ != 0:
            raise Error("invalid class for '[{}]' (should be a 'Control' bundle)".
                    format(section))
        elif id_ != 0:
            if id_ != BundleDescriptor.bundle_id:
                warnings.warn("non-incremental id for '[{}]'".format(section))
            BundleDescriptor.bundle_id += 1
        self.id_ = id_
        self._class = class_
        self.cports = []

    @property
    def class_num(self):
        return self._class

    @property
    def class_name(self):
        try:
            return self.bundle_class[self._class]
        except KeyError:
            return "Reserved"

    def add_cport(self, desc):
        self.used = True
        self.cports.append(desc)

    def __str__(self):
        r = "; '{}' class on Bundle {}\n".format(self.class_name, self.id_)
        r += "[{} {:#x}]\n".format(MnfsParser.BUNDLE_DESC, self.id_)
        r += "class = {:#x}\n".format(self.class_num)
        return r

class CPortDescriptor(Descriptor):

    cport_protocol = {
            0x00: ('Control'            , 0x00),
            0x01: ('AP'                 , 0x01),
            0x02: ('GPIO'               , 0x0a),
            0x03: ('I2C'                , 0x0a),
            0x04: ('UART'               , 0x0a),
            0x05: ('HID'                , 0x05),
            0x06: ('USB'                , 0x0a),
            0x07: ('SDIO'               , 0x0a),
            0x08: ('Power Supply'       , 0x08),
            0x09: ('PWM'                , 0x0a),
            0x0b: ('SPI'                , 0x0a),
            0x0c: ('Display'            , 0x0c),
            0x0d: ('Camera Management'  , 0x0d),
            0x0e: ('Sensor'             , 0x0e),
            0x0f: ('Lights'             , 0x0f),
            0x10: ('Vibrator'           , 0x10),
            0x11: ('Loopback'           , 0x11),
            0x12: ('Audio Management'   , 0x12),
            0x13: ('Audio Data'         , 0x12),
            0x14: ('SVC'                , 0x14),
            0x15: ('Firmware'           , 0x15),
            0x16: ('Camera Data'        , 0x0d),
            0xfe: ('Raw'                , 0xfe),
            0xff: ('Vendor Specific'    , 0xff),
            }

    def __init__(self, id_, bundle, protocol, section):
        super(CPortDescriptor, self).__init__(section, True)
        if id_ == 0 and protocol != 0:
            raise Error("invalid protocol for '[{}]' (should be a 'Control' CPort)"
                    .format(section))
        self.id_ = id_
        self.bundle = bundle
        self._protocol = protocol

    @property
    def protocol_data(self):
        try:
            return self.cport_protocol[self._protocol]
        except KeyError:
            return ("Reserved", None)

    @property
    def protocol_num(self):
        return self._protocol

    @property
    def protocol_name(self):
        return self.protocol_data[0]

    @property
    def protocol_class(self):
        return self.protocol_data[1]

    def __str__(self):
        r = "; '{}' protocol on CPort {}\n".format(self.protocol_name,
                self.id_)
        r += "[{} {:#x}]\n".format(MnfsParser.CPORT_DESC, self.id_)
        r += "bundle = {:#x}\n".format(self.bundle)
        r += "protocol = {:#x}\n".format(self.protocol_num)
        return r

class PropertyDescriptor(Descriptor):

    PROP_VALUE_SIZE = {
            0x00: 1,
            0x01: 1,
            0x02: 1,
            0x03: 1,
            0x04: 2,
            0x05: 4,
            0x06: 8,
            0x07: 1,
            0x08: 1
            }

    def __init__(self, id_, name_stringid, typ, value, section):
        super(PropertyDescriptor, self).__init__(section)
        if id_ == 0:
            raise Error("invalid id for '[{}]' (cannot be 0)".format(section))
        self.id_ = id_
        self.name_stringid = name_stringid
        self.typ = typ
        self.value = value
        self._parent = None

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, desc):
        if self._parent is not None:
            raise Error("multiple references to [{}]".format(self.section))
        self.used = True
        self._parent = desc

    def __str__(self):
        r = ""
        r += "[{} {:#x}]\n".format(MnfsParser.PROPERTY_DESC, self.id_)
        r += "name-string-id = {}\n".format(self.name_stringid)
        r += "type = {}\n".format(self.typ)
        r += "value = <{}>\n".format(str(self.value).replace('[','').replace(']','').replace(',',''))
        return r

class DeviceDescriptor(Descriptor):

    def __init__(self, id_, props, section):
        super(DeviceDescriptor, self).__init__(section)
        self.id_ = id_        
        self.driver_string_id = props[0]
        self.protocol = props[1]
        self.reg = props[2]
        self.irq = props[3]
        self.irq_type = props[4]
        self.max_speed_hz = props[5]
        self.mode = props[6]
        self.prop_link = props[7]
        self.gpio_link = props[8]
        self.reg_link = props[9]
        self.clock_link = props[10]

    def __str__(self):
        r = "[{} {:#x}]\n".format(MnfsParser.DEVICE_DESC, self.id_)
        r += "driver-string-id = {:#x}\n".format(self.driver_string_id)
        r += "protocol = {:#x}\n".format(self.protocol)
        r += "reg = {:#x}\n".format(self.reg)
        r += "irq = {:#x}\n".format(self.irq)
        r += "irq-type = {:#x}\n".format(self.irq_type)
        r += "max-speed-hz = {:#x}\n".format(self.max_speed_hz)
        r += "mode = {:#x}\n".format(self.mode)
        r += "prop-link = {:#x}\n".format(self.prop_link)
        r += "gpio-link = {:#x}\n".format(self.gpio_link)
        r += "reg-link = {:#x}\n".format(self.reg_link)
        r += "clock-link = {:#x}\n".format(self.clock_link)
        return r

### File parsers
class MnfsParser(object):

    # strings
    MNFS_HEADER         = 'manifest-header'
    MNFS_HEADER_VMAJ    = 'version-major'
    MNFS_HEADER_VMIN    = 'version-minor'
    MIKROBUS_DESC      = 'mikrobus-descriptor'
    MNFS_MIKROBUS_PWM_STATE = 'pwm-state'
    MNFS_MIKROBUS_INT_STATE = 'int-state'
    MNFS_MIKROBUS_RX_STATE = 'rx-state'
    MNFS_MIKROBUS_TX_STATE = 'tx-state'
    MNFS_MIKROBUS_SCL_STATE = 'scl-state'
    MNFS_MIKROBUS_SDA_STATE = 'sda-state'
    MNFS_MIKROBUS_MOSI_STATE = 'mosi-state'
    MNFS_MIKROBUS_MISO_STATE = 'miso-state'
    MNFS_MIKROBUS_SCK_STATE = 'sck-state'
    MNFS_MIKROBUS_CS_STATE = 'cs-state'
    MNFS_MIKROBUS_RST_STATE = 'rst-state'
    MNFS_MIKROBUS_AN_STATE = 'an-state'
    INTERFACE_DESC      = 'interface-descriptor'
    INTERFACE_DESC_VSID = 'vendor-string-id'
    INTERFACE_DESC_PSID = 'product-string-id'
    BUNDLE_DESC         = 'bundle-descriptor'
    BUNDLE_DESC_CLASS   = 'class'
    CPORT_DESC          = 'cport-descriptor'
    CPORT_DESC_BUNDLE   = 'bundle'
    CPORT_DESC_PROTOCOL = 'protocol'
    STRING_DESC         = 'string-descriptor'
    STRING_DESC_STRING  = 'string'
    DEVICE_DESC         = 'device-descriptor'
    DEVICE_DESC_DRIVER_STRING_ID   = 'driver-string-id'
    DEVICE_DESC_MAX_SPEED_HZ   = 'max-speed-hz'
    DEVICE_DESC_MODE   = 'mode'
    DEVICE_DESC_PROTOCOL   = 'protocol'
    DEVICE_DESC_REG   = 'reg'
    DEVICE_DESC_IRQ   = 'irq'
    DEVICE_DESC_IRQ_TYPE   = 'irq-type'
    DEVICE_DESC_PROP_LINK   = 'prop-link'
    DEVICE_DESC_GPIO_LINK   = 'gpio-link'
    DEVICE_DESC_REG_LINK   = 'reg-link'
    DEVICE_DESC_CLOCK_LINK   = 'clock-link'
    PROPERTY_DESC         = 'property-descriptor'
    PROPERTY_DESC_NAME_STRING_ID  = 'name-string-id'
    PROPERTY_DESC_TYPE  = 'type'
    PROPERTY_DESC_VALUE  = 'value'

    # sizes
    MNFS_HEADER_VERSION_SIZE    = 1
    ID_DESC_SIZE                = 1
    MAX_SPEED_DESC_SIZE         = 4
    STRING_DESC_STRING_SIZE     = 255
    PROP_DESC_VALUE_SIZE        = 255
    BUNDLE_DESC_CLASS_SIZE      = 1
    CPORT_ID_DESC_SIZE          = 2
    CPORT_DESC_PROTOCOL_SIZE    = 1

    def __init__(self):
        pass

    def __check_int(self, int_val, num_bytes):
        min_ = 0
        max_ = 2**(8 * num_bytes) - 1
        if int_val < min_ or int_val > max_:
            raise ValueError("out of range ([{}:{}])".format(min_, max_))
        return int_val

    def __parse_id(self, section, num_bytes):
        try:
            # Accepted syntax is '<descriptor-type> <id>'
            # and id can be double-quoted.
            id_ = int(section.split()[1].strip('"'), base=0)
            return self.__check_int(id_, num_bytes)
        except IndexError:
            raise Error("missing id value in '[{}]'".format(section))
        except ValueError as e:
            raise Error("invalid id value in '[{}]': {}"
                    .format(section, str(e)))

    def __get_option(self, cfg_parser, section, option_name):
        try:
            return cfg_parser.get(section, option_name)
        except configparser.NoOptionError as e:
            raise Error("missing field '{}' in '[{}]'".format(option_name,
                section))
    
    def __check_option(self, cfg_parser, section, option_name):
        try:
            return cfg_parser.has_option(section, option_name)
        except configparser.NoOptionError as e:
            raise Error("failed to check field '{}' in '[{}]'".format(option_name,
                section))

    def __get_int_option(self, cfg_parser, section, option_name, num_bytes):
        try:
            str_opt = self.__get_option(cfg_parser, section, option_name)
            int_opt =  int(str_opt, base=0)
            return self.__check_int(int_opt, num_bytes)
        except ValueError as e:
            raise Error("invalid value '{}' for field '{}' in '[{}]': {}"
                    .format(str_opt, option_name, section, str(e)))

    def __get_str_option(self, cfg_parser, section, option_name, max_):
        str_opt = self.__get_option(cfg_parser, section, option_name)
        if len(str_opt) > max_:
            raise Error("string '{}' for field '{}' in '[{}]' "
            "is too long (maximum is {})".format(str_opt, option_name, section,
                max_))
        return str_opt
    
    def __get_arr_option(self, cfg_parser, section, option_name, max_, typ):
        arr_opt = self.__get_option(cfg_parser, section, option_name)
        if len(arr_opt) > max_:
            raise Error("arr '{}' for field '{}' in '[{}]' "
            "is too long (maximum is {})".format(arr_opt, option_name, section,
                max_)) 
        if not (arr_opt[0] == '<' and arr_opt[-1] == '>'):
            raise Error("arr '{}' for field '{}' in '[{}]' "
            "does not start with < or end with >".format(arr_opt, option_name, section))
        val = list(map(int, (arr_opt[1:(len(arr_opt)-1)]).split()))
        for values in val:
            self.__check_int(values, PropertyDescriptor.PROP_VALUE_SIZE[typ])
        return val

    def parse_file(self, mnfs_file):
        # force an OrderedDict to get deterministic output even on Python 2.6.
        cfg_parser = configparser.ConfigParser(dict_type=collections.OrderedDict)

        with open(mnfs_file, 'r') as f:
            cfg_parser.read_file(f)

        manifest = Manifest()

        # the error reporting in this function is purely syntaxical

        for section in cfg_parser.sections():
            if section != section.strip():
                raise Error("invalid spaces in '[{}]'".format(section))

            if section == MnfsParser.MNFS_HEADER:
                vmaj = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_HEADER_VMAJ,
                        MnfsParser.MNFS_HEADER_VERSION_SIZE)
                vmin = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_HEADER_VMIN,
                        MnfsParser.MNFS_HEADER_VERSION_SIZE)
                header = ManifestHeader(vmaj, vmin)
                manifest.add_header(header)

            elif section == MnfsParser.INTERFACE_DESC:
                vsid = self.__get_int_option(cfg_parser, section,
                        MnfsParser.INTERFACE_DESC_VSID,
                        MnfsParser.ID_DESC_SIZE)
                psid = self.__get_int_option(cfg_parser, section,
                        MnfsParser.INTERFACE_DESC_PSID,
                        MnfsParser.ID_DESC_SIZE)

                interface = InterfaceDescriptor(vsid, psid, section)
                manifest.add_interface_desc(interface)
            
            elif section == MnfsParser.MIKROBUS_DESC:
                pwm = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_PWM_STATE,
                        MnfsParser.ID_DESC_SIZE)
                _int = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_INT_STATE,
                        MnfsParser.ID_DESC_SIZE)
                rx = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_RX_STATE,
                        MnfsParser.ID_DESC_SIZE)
                tx = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_TX_STATE,
                        MnfsParser.ID_DESC_SIZE)
                scl = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_SCL_STATE,
                        MnfsParser.ID_DESC_SIZE)
                sda = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_SDA_STATE,
                        MnfsParser.ID_DESC_SIZE)
                mosi = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_MOSI_STATE,
                        MnfsParser.ID_DESC_SIZE)
                miso = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_MISO_STATE,
                        MnfsParser.ID_DESC_SIZE)
                sck = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_SCK_STATE,
                        MnfsParser.ID_DESC_SIZE)
                cs = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_CS_STATE,
                        MnfsParser.ID_DESC_SIZE)
                rst = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_RST_STATE,
                        MnfsParser.ID_DESC_SIZE)
                an = self.__get_int_option(cfg_parser, section,
                        MnfsParser.MNFS_MIKROBUS_AN_STATE,
                        MnfsParser.ID_DESC_SIZE)
                mikrobus = MikrobusDescriptor(pwm, _int, rx, tx, scl, \
                            sda, mosi, miso, sck, cs, rst, an, section)
                manifest.add_mikrobus_desc(mikrobus)

            elif section.split()[0] == MnfsParser.STRING_DESC:
                id_ = self.__parse_id(section, MnfsParser.ID_DESC_SIZE)
                str_ = self.__get_str_option(cfg_parser, section,
                        MnfsParser.STRING_DESC_STRING,
                        MnfsParser.STRING_DESC_STRING_SIZE)

                string = StringDescriptor(id_, str_, section)
                manifest.add_string_desc(string)
            
            elif section.split()[0] == MnfsParser.PROPERTY_DESC:
                id_ = self.__parse_id(section, MnfsParser.ID_DESC_SIZE)
                name_stringid = self.__get_int_option(cfg_parser, section,
                        MnfsParser.PROPERTY_DESC_NAME_STRING_ID,
                        MnfsParser.ID_DESC_SIZE)
                typ = self.__get_int_option(cfg_parser, section,
                        MnfsParser.PROPERTY_DESC_TYPE,
                        MnfsParser.ID_DESC_SIZE)
                value = self.__get_arr_option(cfg_parser, section,
                        MnfsParser.PROPERTY_DESC_VALUE,
                        MnfsParser.PROP_DESC_VALUE_SIZE, typ)
                prop = PropertyDescriptor(id_, name_stringid, typ, value, section)
                manifest.add_property_desc(prop)
            
            elif section.split()[0] == MnfsParser.BUNDLE_DESC:
                id_ = self.__parse_id(section, MnfsParser.ID_DESC_SIZE)
                class_ = self.__get_int_option(cfg_parser, section,
                        MnfsParser.BUNDLE_DESC_CLASS,
                        MnfsParser.BUNDLE_DESC_CLASS_SIZE)

                bundle = BundleDescriptor(id_, class_, section)
                manifest.add_bundle_desc(bundle)

            elif section.split()[0] == MnfsParser.CPORT_DESC:
                id_ = self.__parse_id(section, MnfsParser.CPORT_ID_DESC_SIZE)
                bundle = self.__get_int_option(cfg_parser, section,
                        MnfsParser.CPORT_DESC_BUNDLE,
                        MnfsParser.ID_DESC_SIZE)
                protocol = self.__get_int_option(cfg_parser, section,
                        MnfsParser.CPORT_DESC_PROTOCOL,
                        MnfsParser.CPORT_DESC_PROTOCOL_SIZE)

                cport = CPortDescriptor(id_, bundle, protocol, section)
                manifest.add_cport_desc(cport)

            elif section.split()[0] == MnfsParser.DEVICE_DESC:
                id_ = self.__parse_id(section, MnfsParser.ID_DESC_SIZE)
                driverstr = self.__get_int_option(cfg_parser, section,
                        MnfsParser.DEVICE_DESC_DRIVER_STRING_ID,
                        MnfsParser.ID_DESC_SIZE)
                protocol = self.__get_int_option(cfg_parser, section,
                        MnfsParser.DEVICE_DESC_PROTOCOL,
                        MnfsParser.ID_DESC_SIZE)
                if protocol == 11:
                    maxspeedhz = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_MAX_SPEED_HZ,
                            MnfsParser.MAX_SPEED_DESC_SIZE)
                    mode = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_MODE,
                            MnfsParser.ID_DESC_SIZE)
                else:
                    maxspeedhz=0
                    mode=0
                if protocol != 4:
                    reg = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_REG,
                            MnfsParser.ID_DESC_SIZE)
                else:
                    reg = 0
                if (self.__check_option(cfg_parser, section,
                        MnfsParser.DEVICE_DESC_IRQ)):
                    irq = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_IRQ,
                            MnfsParser.ID_DESC_SIZE)
                    irq_type = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_IRQ_TYPE,
                            MnfsParser.ID_DESC_SIZE)
                else:
                    irq= 0
                    irq_type= 0
                if (self.__check_option(cfg_parser, section,
                        MnfsParser.DEVICE_DESC_PROP_LINK)):      
                    prop_link = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_PROP_LINK,
                            MnfsParser.ID_DESC_SIZE)
                else:
                    prop_link = 0
                if (self.__check_option(cfg_parser, section,
                        MnfsParser.DEVICE_DESC_GPIO_LINK)):   
                    gpio_link = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_GPIO_LINK,
                            MnfsParser.ID_DESC_SIZE)
                else:
                    gpio_link = 0
                if (self.__check_option(cfg_parser, section,
                        MnfsParser.DEVICE_DESC_REG_LINK)):   
                    reg_link = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_REG_LINK,
                            MnfsParser.ID_DESC_SIZE)
                else:
                    reg_link = 0
                if (self.__check_option(cfg_parser, section,
                        MnfsParser.DEVICE_DESC_CLOCK_LINK)):   
                    clock_link = self.__get_int_option(cfg_parser, section,
                            MnfsParser.DEVICE_DESC_CLOCK_LINK,
                            MnfsParser.ID_DESC_SIZE)
                else:
                    clock_link = 0          
                props = [driverstr, protocol, reg, irq, irq_type, \
                     maxspeedhz, mode, prop_link, gpio_link, reg_link, clock_link]
                device = DeviceDescriptor(id_, props, section)
                manifest.add_device_desc(device)
            else:
                raise Error("invalid descriptor '[{}]'".format(section))

        return manifest