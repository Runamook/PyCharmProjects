#!/usr/bin/pwsh

# Infile - CSV
# Juniper SRX Router 10.11.0.1 - ACFRA0020001;10.11.0.1
# 10.11.30.63;10.11.30.63


$filename = '/home/eg/Scripts/vpn.csv'
$result_filename = '/tmp/vpn_results.txt'
$delimiter = ';'

$header = '{"data":['
$footer = ']}'
$lineTemplate = '{{"{{#VPNNAME}}":"{0}", "{{#VPNADDR}}":"{1}"}}'

$content = Get-Content $filename
$total = $content.Count;
$counter = 0
$result = $header
foreach ($line in $content) {
    $counter++
    $splitted = $line.Split($delimiter)
    if ($splitted.Length -ne 2) {
        continue;
    }
    $result += ($lineTemplate -f $splitted[0], $splitted[1])
    if ($counter -ne $total) {
        $result += ' , '
    }
}
$result += $footer
$result > $result_filename

$content = Get-Content $result_filename
foreach ($line in $content)
{
    Write-Host $line
}
