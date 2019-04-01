#!/usr/bin/pwsh

$content = Get-Content /home/eg/Scripts/vpn.txt
foreach ($line in $content)
{
    Write-Host $line
}

{"data":[{"{#VPNNAME}":"Juniper SRX Router 10.11.0.1 - ACFRA0020001", "{#VPNADDR}":"10.11.0.1"} , {"{#VPNNAME}":"10.11.30.63", "{#VPNADDR}":"10.11.30.63"} , {"{#VPNNAME}":"EHM-Variomod 172.17.60.200", "{#VPNADDR}":"172.17.60.200"} , {"{#VPNNAME}":"EHM-Variomod 172.17.90.171", "{#VPNADDR}":"172.17.90.171"} , {"{#VPNNAME}":"EHM-Variomod 172.17.90.172", "{#VPNADDR}":"172.17.90.172"} , {"{#VPNNAME}":"Enercon EHM-Variomod 172.17.90.227", "{#VPNADDR}":"172.17.90.227"} , {"{#VPNNAME}":"Google", "{#VPNADDR}":"8.8.8.8"} , {"{#VPNNAME}":"Cloudflare", "{#VPNADDR}":"1.1.1.1"}]}