#!/usr/bin/env python

import paho.mqtt.client as mqtt
import base64
import zlib
import json
from graphviz import Digraph
import signal
import sys
from pprint import pprint

agent_c = "blue"
entity_c = "khaki1"
activity_c = "lightsteelblue1"
agent_s = "circle"
entity_s = "ellipse"
activity_s = "box"
map_nodes = {}
filter_nodes = []
tryEdgeAgain = []
dot = Digraph('G',format='pdf')
dot.graph_attr.update(ratio="fill")
dot.node_attr.update(fontname="Helvetica-Bold",style="filled,setlinewidth(5)", margin="0.1,0.1",fontsize="40")
dot.edge_attr.update(fontname="Helvetica-Bold", fontsize="40",weight="1",penwidth="8",arrowsize="2")
total_json = {}


def edge_again():
    global tryEdgeAgain
    again = []
    while len(tryEdgeAgain) > 0:
	edge = tryEdgeAgain.pop()
	if (existNode(edge['src']) and existNode(edge['dest'])):
	    dot.edge( edge['src'][3:], edge['dest'][3:], color = edge['color'], label = edge['label'] )
	else:
	    again.append(edge)
    tryEdgeAgain = again

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    edge_again()
    dot.render('./provenance')
    with open('./python_camflow_graph.dot','w') as fil:
        fil.write(str(dot))
        
    with open('./python_camflow_graph.json','w') as fil:
        pprint(total_json,stream=fil,indent=2)
    sys.exit(0)

def insertNode(key, label, color, shape):
    if (label.startswith("[envp]")):
	filter_nodes.append(key);
	return;
    if(label is None):
	label = key
    map_nodes[key] = True
    dot.node( key[3:], fillcolor=color, shape=shape, label=label )

def parse_entities(entities):
    for key, dic in entities.items():
        label = ""
        if(dic.get('prov:label') is not None):
	    label = dic['prov:label']
	elif(dic.get('rdt:name') is not None):
	    label = dic['rdt:name']+' ['+dic['rdt:type']+']'
	else:
	    label = key
            
        if(entities[key]['prov:type']=='prov:agent'):
	    insertNode(key, label, agent_c, agent_s);
	else:
	    insertNode(key, label, entity_c, entity_s);

def parse_activities(activities):
    for key, dic in activities.items():
        label = ""
        if(dic.get('prov:label') is not None):
	    label = dic['prov:label']
	elif(dic.get('rdt:name') is not None):
            if(dic['rdt:startLine'] is not 'NA'):
                label = dic['rdt:name']+'['+dic['rdt:type']+'](Line: '+dic['rdt:startLine']+')';
	    else:
		label = dic['rdt:name']+' ['+dic['rdt:type']+']';
	else:
	    label = key

        if (dic.get('cf:pid') is not None):
	    label = label + "\n PID=" + str(dic['cf:pid'])
	if (dic.get('cf:uid') is not None ):
	    label = label + "\n UID=" + str(dic['cf:uid'])
	if (dic.get('cf:tgid') is not None):
	    label = label + "\n TGID=" + str(dic['cf:tgid'])
            
	insertNode(key, label, activity_c, activity_s)


def existNode(node):
    if node in map_nodes:
	return True
    else:
        return False

def parse_agents(agents):
    
    for key in agents:
	insertNode( key, None, agent_c, agent_s)

def insertEdge(src, dest, label, color, check):
    if (existNode(src) and existNode(dest)):
	dot.edge( src[3:], dest[3:], color = color, label = label )
    else:
	tryEdgeAgain.append({'src': str(src), 'dest': str(dest), 'label': label, 'color': color})

def parse_edges(eles, key1, key2, color, prelabel, check=""):
    for key,dic in eles.items():
	if dic.get('prov:label') is not None:
	   insertEdge(str(dic[key1]), str(dic[key2]), prelabel +" - "+ dic['prov:label'], color, check)
	else:
	    insertEdge(str(dic[key1]), str(dic[key2]), prelabel, color, check);
    
def parse_double_edges(eles, key1, key2, neston, nest1, nest2):
    for key,dic in eles.items():
	insertEdge(dic[key1], dic[key2], '#00CCCC', 'wasAssociatedWith');

def parse_nested_edges(eles, key1, key2, neston, nest1, nest2):
    for key,dic in eles.items():
	insertEdge(dic[key1], dic[key2], '#CC00CC', 'derivedByInsertionFrom')

    
def combineDictVal(total_json, new_json):
    for key, value in new_json.items():
        if key not in total_json:
            total_json[key] = value
        else:
            total_json[key].update(value)
    return total_json

def parse(json_msg):
    parsed_json = json.loads(json_msg)
    global total_json
    # if (len(total_json) > 0):
    #     total_json = parsed_json
    # else:
    #     total_json.update(parsed_json)
    total_json = combineDictVal(total_json,parsed_json)
    print("size of dictionary ", str(len(total_json)))
    lengths = [len(v) for v in total_json.values()]
    print(lengths)
    # TODO javascript code uses extend function here which I don't understand
    if parsed_json.get('entity') is not None:
        parse_entities(parsed_json['entity'])
    if parsed_json.get('activity') is not None:
        parse_activities(parsed_json['activity'])
    if parsed_json.get('agent') is not None:
        parse_agents(parsed_json['agent'])
           
    edge_again()
    if parsed_json.get('wasGeneratedBy') is not None:
        parse_edges(parsed_json['wasGeneratedBy'], 'prov:entity', 'prov:activity', '#0000FF', 'wasGeneratedBy');

    if parsed_json.get('used') is not None:
        parse_edges(parsed_json.get('used'), 'prov:activity', 'prov:entity', '#00FF00', 'used');

    if parsed_json.get('wasDerivedFrom') is not None:
        parse_edges(parsed_json.get('wasDerivedFrom') , 'prov:generatedEntity', 'prov:usedEntity', '#FF9933', 'wasDerivedFrom', "now")

    if parsed_json.get('wasAttributedTo') is not None:
        parse_edges(parsed_json.get('wasAttributedTo'), 'prov:entity', 'prov:agent', '#00CCCC', 'wasAttributedTo')
           
    if parsed_json.get('wasInformedBy') is not None:
        parse_edges(parsed_json.get('wasInformedBy') , 'prov:informed', 'prov:informant', '#CC00CC', 'wasInformedBy')					

    if parsed_json.get('specializationOf') is not None:
        parse_edges(parsed_json.get('specializationOf'), 'prov:entity', 'prov:secialization', '#CC00CC', 'specializationOf')
    if parsed_json.get('alternateOf') is not None:
        parse_edges(parsed_json.get('alternateOf'), 'prov:entity', 'prov:alternae', '#CC00CC', 'alternateOf')

    if parsed_json.get('relation') is not None:
        parse_edges(parsed_json.get('relation'), 'cf:receiver', 'cf:sender', '#FF0000', 'genericRelation')

    if parsed_json.get('wasAssociatedWith') is not None:
        parse_double_edges(parsed_json.get('wasAssociatedWith') , 'prov:activity', 'prov:agent', 'prov:plan', 'prov:agent', 'prov:plan')

    if parsed_json.get('derivedByInsertionFrom') is not None:
        parse_nested_edges(parsed_json.get('derivedByInsertionFrom') , 'prov:before','prov:after', 'prov:key-entity-set', 'prov:after','prov:key-entity-set')
    edge_again()
           
def on_connect(client, userdata, flags, rc):
    print("Connected\n")

# The callback for when a message is received from the server.
def on_message(client, userdata, msg):
    # print(msg.topic+" "+str(msg.payload))
    json_str = zlib.decompress(base64.b64decode(msg.payload))
    parse(json_str)
    
if __name__ == '__main__':
    client = mqtt.Client()
    client.username_pw_set("kyekdxmk", "J6Y-kjN1-NbO")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("m12.cloudmqtt.com", 11724, 60)
    client.subscribe("camflow/provenance/2098989664", qos=1)
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    signal.signal(signal.SIGINT, signal_handler)
    client.loop_forever()
