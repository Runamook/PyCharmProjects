
def item_header(tpl_name):
    result = '''<?xml version="1.0" encoding="UTF-8"?>
    <zabbix_export>
        <version>4.0</version>
        <date>2019-03-29T13:00:43Z</date>
        <groups>
            <group>
                <name>Templates</name>
            </group>
        </groups>
        <templates>
            <template>
                <template>Template %s</template>
                <name>Template %s</name>
                <description/>
                <groups>
                    <group>
                        <name>Templates</name>
                    </group>
                </groups>
                <applications>
                    <application>
                        <name>VPN</name>
                    </application>
                </applications>
                <items>
    ''' % (tpl_name, tpl_name)
    return result


def item1(item_name, item_addr):
    result = '''                <item>
                        <name>%s</name>
                        <type>0</type>
                        <snmp_community/>
                        <snmp_oid/>
                        <key>VPNCheck[%s]</key>
                        <delay>{$INTERVAL}</delay>
                        <history>14d</history>
                        <trends>365d</trends>
                        <status>0</status>
                        <value_type>3</value_type>
                        <allowed_hosts/>
                        <units/>
                        <snmpv3_contextname/>
                        <snmpv3_securityname/>
                        <snmpv3_securitylevel>0</snmpv3_securitylevel>
                        <snmpv3_authprotocol>0</snmpv3_authprotocol>
                        <snmpv3_authpassphrase/>
                        <snmpv3_privprotocol>0</snmpv3_privprotocol>
                        <snmpv3_privpassphrase/>
                        <params/>
                        <ipmi_sensor/>
                        <authtype>0</authtype>
                        <username/>
                        <password/>
                        <publickey/>
                        <privatekey/>
                        <port/>
                        <description/>
                        <inventory_link>0</inventory_link>
                        <applications>
                            <application>
                                <name>VPN</name>
                            </application>
                        </applications>
                        <valuemap/>
                        <logtimefmt/>
                        <preprocessing/>
                        <jmx_endpoint/>
                        <timeout>3s</timeout>
                        <url/>
                        <query_fields/>
                        <posts/>
                        <status_codes>200</status_codes>
                        <follow_redirects>1</follow_redirects>
                        <post_type>0</post_type>
                        <http_proxy/>
                        <headers/>
                        <retrieve_mode>0</retrieve_mode>
                        <request_method>0</request_method>
                        <output_format>0</output_format>
                        <allow_traps>0</allow_traps>
                        <ssl_cert_file/>
                        <ssl_key_file/>
                        <ssl_key_password/>
                        <verify_peer>0</verify_peer>
                        <verify_host>0</verify_host>
                        <master_item/>
                    </item>
    ''' % (item_name, item_addr)
    return result


def item2(item_name, item_addr):
    result = '''                 <item>
                        <name>%s Delay</name>
                        <type>0</type>
                        <snmp_community/>
                        <snmp_oid/>
                        <key>VPNDelay[%s]</key>
                        <delay>{$INTERVAL}</delay>
                        <history>14d</history>
                        <trends>365d</trends>
                        <status>0</status>
                        <value_type>3</value_type>
                        <allowed_hosts/>
                        <units/>
                        <snmpv3_contextname/>
                        <snmpv3_securityname/>
                        <snmpv3_securitylevel>0</snmpv3_securitylevel>
                        <snmpv3_authprotocol>0</snmpv3_authprotocol>
                        <snmpv3_authpassphrase/>
                        <snmpv3_privprotocol>0</snmpv3_privprotocol>
                        <snmpv3_privpassphrase/>
                        <params/>
                        <ipmi_sensor/>
                        <authtype>0</authtype>
                        <username/>
                        <password/>
                        <publickey/>
                        <privatekey/>
                        <port/>
                        <description/>
                        <inventory_link>0</inventory_link>
                        <applications>
                            <application>
                                <name>VPN</name>
                            </application>
                        </applications>
                        <valuemap/>
                        <logtimefmt/>
                        <preprocessing>
                            <step>
                                <type>5</type>
                                <params>.*Average = (\d+)ms
    \\1</params>
                            </step>
                        </preprocessing>
                        <jmx_endpoint/>
                        <timeout>3s</timeout>
                        <url/>
                        <query_fields/>
                        <posts/>
                        <status_codes>200</status_codes>
                        <follow_redirects>1</follow_redirects>
                        <post_type>0</post_type>
                        <http_proxy/>
                        <headers/>
                        <retrieve_mode>0</retrieve_mode>
                        <request_method>0</request_method>
                        <output_format>0</output_format>
                        <allow_traps>0</allow_traps>
                        <ssl_cert_file/>
                        <ssl_key_file/>
                        <ssl_key_password/>
                        <verify_peer>0</verify_peer>
                        <verify_host>0</verify_host>
                        <master_item/>
                    </item>
    ''' % (item_name, item_addr)
    return result


def item_trailer():
    result = '''            </items>
            <discovery_rules/>
            <httptests/>
            <macros>
                <macro>
                    <macro>{$INTERVAL}</macro>
                    <value>5m</value>
                </macro>
            </macros>
            <templates/>
            <screens/>
        </template>
    </templates>
    <triggers>
    '''
    return result


def trigger1(tpl_name, item_addr, item_name):
    result = '''        <trigger>
            <expression>{Template %s:VPNCheck[%s].last()}=0</expression>
            <recovery_mode>0</recovery_mode>
            <recovery_expression/>
            <name>VPN tunnel down %s</name>
            <correlation_mode>0</correlation_mode>
            <correlation_tag/>
            <url/>
            <status>0</status>
            <priority>4</priority>
            <description/>
            <type>0</type>
            <manual_close>0</manual_close>
            <dependencies/>
            <tags>
                <tag>
                    <tag>Application</tag>
                    <value>VPN</value>
                </tag>
            </tags>
        </trigger>
    ''' % (tpl_name, item_addr, item_name)
    return result


def trigger2(tpl_name, item_addr, item_name):
    result = '''        <trigger>
            <expression>{Template %s:VPNDelay[%s].last()}&gt;100</expression>
            <recovery_mode>0</recovery_mode>
            <recovery_expression/>
            <name>VPN tunnel high delay %s</name>
            <correlation_mode>0</correlation_mode>
            <correlation_tag/>
            <url/>
            <status>0</status>
            <priority>4</priority>
            <description/>
            <type>0</type>
            <manual_close>0</manual_close>
            <dependencies/>
            <tags>
                <tag>
                    <tag>Application</tag>
                    <value>VPN</value>
                </tag>
            </tags>
        </trigger>
    ''' % (tpl_name, item_addr, item_name)
    return result


def trigger_trailer():
    result = '''    </triggers>
    </zabbix_export>
    '''
    return result
