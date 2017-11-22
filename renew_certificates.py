import json;
import sys;
from subprocess import call;
import dbus;
import os;
import acme_tiny;
import logging;
from contextlib import redirect_stdout
# Shell calls (as subprocedure)
#call('ls')

csr_out_dir = "/tmp/csr/"
crt_out_dir = "/etc/ssl/mycerts/"
account_key = "/etc/ssl/private/letsencrypt/account.key"
acme_dir = "/var/www/acme-challenges/"
webserver_unit = "nginx.service"
ca_crt_file = "/etc/ssl/mycerts/letsencryptx3.crt"
domain_list = '/etc/ssl/private/letsencrypt/domain-list.json'
command = [
 'openssl req -new -sha256 -key /etc/ssl/private/',
 '.key -subj "/" -reqexts SAN -config <(cat /etc/ssl/openssl.cnf <(printf "[SAN]\nsubjectAltName=',
 '")) > ' + csr_out_dir,
 '.csr; '
]

def main():
 # Import json
 with open(domain_list) as json_data:
  domainlist = json.load(json_data)
 # Load intermediate ca file to append it to the certificate
 ca_crt_content = ""
 with open(ca_crt_file) as content:
  ca_crt_content = content.read()

 # Join command
 #openssl req -new -sha256 -key domain.key -subj "/" -reqexts SAN -config <(cat /etc/ssl/openssl.cnf <(printf "[SAN]\nsubjectAltName=DNS:yoursite.com,DNS:www.yoursite.com")) > domain.csr
 full_command = ""
 for domain in domainlist:
  prefix_command = command[0] + domain["Domain"] + command[1]
  middle_command = ""
  for subdomain in domain["Subdomains"]:
   if subdomain != "":
    subdomain = subdomain + "."
   middle_command += "DNS:" + subdomain + domain["Domain"] + ","
  full_command += prefix_command + middle_command[:-1] + command[2] + domain["Domain"] + command[3]

 # OpenSSL generate csr
 call_command = "bash -c '" + "mkdir -p " + csr_out_dir + "; " + full_command + "'"
 call(call_command, shell=True)

 acme_param = [
  "--account-key",
  account_key,
  "--csr",
  csr_out_dir,
  "--acme-dir",
  acme_dir
 ]

 for filename in os.listdir(csr_out_dir):
  acme_param_current = acme_param.copy()
  acme_param_current[3] += filename
  crt_file = crt_out_dir + filename[:-4] + '.crt'
  # get the certificate
  crt_content = acme_tiny.get_crt(acme_param_current[1], acme_param_current[3], acme_param_current[5], acme_tiny.LOGGER, acme_tiny.DEFAULT_CA)
  # add intermediate ca certificate to crt_content

  with open(crt_file, 'w') as crt_file_writer:
#   with redirect_stdout(crt_file_writer):
   crt_file_writer.write(crt_content)
   crt_file_writer.write("\n\n")
   crt_file_writer.write(ca_crt_content)

  # Delete csr file
  if os.path.isfile(csr_out_dir + filename):
   os.remove(csr_out_dir + filename)


 # Reload webserver unit (systemd)
 sysbus = dbus.SystemBus()
 systemd1 = sysbus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
 manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
 manager.Reload() # reload all unit files.
 manager.ReloadOrRestartUnit(webserver_unit, 'fail')

if __name__ == '__main__':
 main()
