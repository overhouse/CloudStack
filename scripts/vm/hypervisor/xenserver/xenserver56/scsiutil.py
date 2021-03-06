# Copyright (c) 2005-2007 XenSource, Inc. All use and distribution of this
# $Id: scsiutil.py 9132 2010-06-04 20:17:43Z manuel $ $HeadURL: svn://svn.lab.vmops.com/repos/branches/2.1.x.beta/java/scripts/vm/hypervisor/xenserver/xenserver56/scsiutil.py $
# copyrighted material is governed by and subject to terms and conditions
# as licensed by XenSource, Inc. All other rights reserved.
# Xen, XenSource and XenEnterprise are either registered trademarks or
# trademarks of XenSource Inc. in the United States and/or other countries.
#
#
# Miscellaneous scsi utility functions
#

import util, SR
import os
import re
import xs_errors
import base64
import time
import errno
import glob

PREFIX_LEN = 4
SUFFIX_LEN = 12
SECTOR_SHIFT = 9

def gen_hash(st, len):
    hs = 0
    for i in st:
        hs = ord(i) + (hs << 6) + (hs << 16) - hs
    return str(hs)[0:len]

def gen_uuid_from_serial(iqn, serial):
    if len(serial) < SUFFIX_LEN:
        raise util.CommandException(1)
    prefix = gen_hash(iqn, PREFIX_LEN)
    suffix = gen_hash(serial, SUFFIX_LEN)
    str = prefix.encode("hex") + suffix.encode("hex")
    return str[0:8]+'-'+str[8:12]+'-'+str[12:16]+'-'+str[16:20]+'-'+str[20:32]

def gen_serial_from_uuid(iqn, uuid):
    str = uuid.replace('-','')
    prefix = gen_hash(iqn, PREFIX_LEN)
    if str[0:(PREFIX_LEN * 2)].decode("hex") != prefix:
        raise util.CommandException(1)
    return str[(PREFIX_LEN * 2):].decode("hex")

def getsize(path):
    dev = getdev(path)
    sysfs = os.path.join('/sys/block',dev,'size')
    size = 0
    if os.path.exists(sysfs):
        try:
            f=open(sysfs, 'r')
            size = (long(f.readline()) << SECTOR_SHIFT)
            f.close()
        except:
            pass
    return size

def getuniqueserial(path):
    dev = getdev(path)
    output = gen_rdmfile()
    try:
        cmd = ["scsi_id", "-g", "-s", "/block/%s" % dev]
        text = util.pread2(cmd)
    
        cmd = ["md5sum"]
        txt = util.pread3(cmd, text)
        return txt.split(' ')[0]
    except:
        return ''

def gen_uuid_from_string(str):
    if len(str) < (PREFIX_LEN + SUFFIX_LEN):
        raise util.CommandException(1)
    return str[0:8]+'-'+str[8:12]+'-'+str[12:16]+'-'+str[16:20]+'-'+str[20:32]

def SCSIid_sanitise(str):
    text = re.sub("^\s+","",str)
    return re.sub("\s+","_",text)

def getSCSIid(path):
    dev = rawdev(path)
    cmd = ["scsi_id", "-g", "-s", "/block/%s" % dev]
    return SCSIid_sanitise(util.pread2(cmd)[:-1])

def getserial(path):
    dev = os.path.join('/dev',getdev(path))
    try:
        cmd = ["sginfo", "-s", dev]
        text = re.sub("\s+","",util.pread2(cmd))
    except:
        raise xs_errors.XenError('EIO', \
              opterr='An error occured querying device serial number [%s]' \
                           % dev)
    try:
        return text.split("'")[1]
    except:
        return ''

def getmanufacturer(path):
    cmd = ["sginfo", "-M", path]
    try:
        for line in filter(match_vendor, util.pread2(cmd).split('\n')):
            return line.replace(' ','').split(':')[-1]
    except:
        return ''

def cacheSCSIidentifiers():
    SCSI = {}
    cmd = ["sg_map", "-x"]
    for line in filter(match_sd, util.pread2(cmd).split('\n')):
        # Output: sg_dev adapter channel id lun type sd_device
        ids = line.split()
        SCSI[ids[6]] = ids
    return SCSI

def scsi_dev_ctrl(ids, cmd):
    f = -1
    for i in range(0,10):
        try:
            str = "scsi %s-single-device %s %s %s %s" % \
                  (cmd, ids[1],ids[2],ids[3],ids[4])
            util.SMlog(str)
            f=open('/proc/scsi/scsi', 'w')
            print >>f, str
            f.close()
            return
        except IOError, e:
            util.SMlog("SCSI_DEV_CTRL: Failure, %s [%d]" % (e.strerror,e.errno))
            if f >= 0:
                f.close()
            if e.errno == errno.ENXIO:
                util.SMlog("Device has disappeared already")
                return
            f = -1
            time.sleep(6)
            continue
    raise xs_errors.XenError('EIO', \
            opterr='An error occured during the scsi operation')

def getdev(path):
    if match_dm(path):
        newpath = path.replace("/dev/mapper/","/dev/disk/by-id/scsi-")
    else:
        newpath = path
    return os.path.realpath(newpath).split('/')[-1]

def rawdev(dev):
    return re.sub("[0-9]*$","",getdev(dev))

def getSessionID(path):
    for line in filter(match_session, util.listdir(path)):
        return line.split('-')[-1]

def match_session(s):
    regex = re.compile("^SESSIONID-")
    return regex.search(s, 0)

def match_vendor(s):
    regex = re.compile("^Vendor:")
    return regex.search(s, 0)

def match_dm(s):
    regex = re.compile("mapper/")
    return regex.search(s, 0)    
    
def match_sd(s):
    regex = re.compile("/dev/sd")
    return regex.search(s, 0)

def _isSCSIdev(dev):
    if match_dm(dev):
        path = dev.replace("/dev/mapper/","/dev/disk/by-id/scsi-")
    else:
        path = dev
    return match_sd(os.path.realpath(path))

def gen_rdmfile():
    return "/tmp/%s" % util.gen_uuid()

def add_serial_record(session, sr_ref, devstring):
    try:
        conf = session.xenapi.SR.get_sm_config(sr_ref)
        conf['devserial'] = devstring
        session.xenapi.SR.set_sm_config(sr_ref, conf)
    except:
        pass

def get_serial_record(session, sr_ref):
    try:
        conf = session.xenapi.SR.get_sm_config(sr_ref)
        return conf['devserial']
    except:
        return ""

def devlist_to_serialstring(devlist):
    serial = ''
    for dev in devlist:
        try:
            devserial = "scsi-%s" % getSCSIid(dev)
            if not len(devserial) > 0:
                continue
            if len(serial):
                serial += ','
            serial += devserial
        except:
            pass
    
    return serial

def gen_synthetic_page_data(uuid):
    # For generating synthetic page data for non-raw LUNs
    # we set the vendor ID to XENSRC
    # Note that the Page 80 serial number must be limited
    # to 16 characters
    page80 = ""
    page80 += "\x00\x80"
    page80 += "\x00\x12"
    page80 += uuid[0:16]
    page80 += "  "
    
    page83 = ""
    page83 += "\x00\x83"
    page83 += "\x00\x31"
    page83 += "\x02\x01\x00\x2d"
    page83 += "XENSRC  "
    page83 += uuid
    page83 += " "
    return ["",base64.b64encode(page80),base64.b64encode(page83)]
    
def gen_raw_page_data(path):
    default = ""
    page80 = ""
    page83 = ""
    try:
        cmd = ["sg_inq", "-r", path]
        text = util.pread2(cmd)
        default = base64.b64encode(text)
            
        cmd = ["sg_inq", "--page=0x80", "-r", path]
        text = util.pread2(cmd)
        page80 = base64.b64encode(text)
            
        cmd = ["sg_inq", "--page=0x83", "-r", path]
        text = util.pread2(cmd)
        page83 = base64.b64encode(text)
    except:
        pass
    return [default,page80,page83]

def update_XS_SCSIdata(session, vdi_ref, vdi_uuid, data):
        try:
            session.xenapi.VDI.remove_from_xenstore_data(vdi_ref, "vdi-uuid")
        except:
            pass
        
        try:
            session.xenapi.VDI.remove_from_xenstore_data(vdi_ref, "scsi/0x12/default")
        except:
            pass
        
        try:
            session.xenapi.VDI.remove_from_xenstore_data(vdi_ref, "scsi/0x12/0x80")
        except:
            pass

        try:
            session.xenapi.VDI.remove_from_xenstore_data(vdi_ref, "scsi/0x12/0x83")
        except:
            pass

        try:
            session.xenapi.VDI.add_to_xenstore_data(vdi_ref, "vdi-uuid", vdi_uuid)
            if len(data[0]):
                session.xenapi.VDI.add_to_xenstore_data(vdi_ref, "scsi/0x12/default", data[0])

            if len(data[1]):
                session.xenapi.VDI.add_to_xenstore_data(vdi_ref, "scsi/0x12/0x80", data[1])

            if len(data[2]):
                session.xenapi.VDI.add_to_xenstore_data(vdi_ref, "scsi/0x12/0x83", data[2])
        except:
            pass

def rescan(ids, scanstring='- - -'):
    for id in ids:
        util.SMlog("Rescanning bus id %s with %s" % (id, scanstring))
        path = '/sys/class/scsi_host/host%s/scan' % id
        if os.path.exists(path):
            try:
                f=open(path, 'w')
                f.write('%s\n' % scanstring)
                f.close()
                #time.sleep(2)
            except:
                pass

def scsi_unplug(vdipath):
    dev = getdev(vdipath)
    util.SMlog("unplug path %s dev %s" % (vdipath, dev))
    path = '/sys/block/%s/device/delete' % dev
    if os.path.exists(path):
        try:
            f=open(path, 'w')
            f.write('1')
            f.close()
            time.sleep(2)
        except: 
            pass



def _genArrayIdentifier(dev):
    try:
        cmd = ["sg_inq", "--page=0xc8", "-r", dev]
        id = util.pread2(cmd)
        return id.encode("hex")[180:212]
    except:
        return ""


def _genHostList(procname):
    # loop through and check all adapters
    ids = []
    try:
        for dir in util.listdir('/sys/class/scsi_host'):
            filename = os.path.join('/sys/class/scsi_host',dir,'proc_name')
            if os.path.exists(filename):
                f = open(filename, 'r')
                if f.readline().find(procname) != -1:
                    ids.append(dir.replace("host",""))
                f.close()
    except:
        pass
    return ids

def _genReverseSCSIidmap(SCSIid):
    util.SMlog("map_by_scsibus: sid=%s" % SCSIid)

    devices = []
    for link in glob.glob('/dev/disk/by-id/scsi-%s' % SCSIid):
        devices.append(os.path.realpath(link))
    return devices

def _dosgscan():
    regex=re.compile("([^:]*):\s+scsi([0-9]+)\s+channel=([0-9]+)\s+id=([0-9]+)\s+lun=([0-9]+)")
    scan=util.pread2(["/usr/bin/sg_scan"]).split('\n')
    sgs=[]
    for line in scan:
        m=regex.match(line)
        if m:
            device=m.group(1)
            host=m.group(2)
            channel=m.group(3)
            sid=m.group(4)
            lun=m.group(5)
            sgs.append([device,host,channel,sid,lun])
    return sgs
