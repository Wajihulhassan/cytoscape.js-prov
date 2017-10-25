#!/usr/bin/env python
import paho.mqtt.client as mqtt
import base64
import zlib
import json
from graphviz import Digraph
import signal
import sys
from pprint import pprint

# TODO Get rid of globals
# Dot file attributes
map_nodes = {}
tryEdgeAgain = []
total_json = {}

def combineDictVal(total_json, new_json):
    for key, value in new_json.items():
        if key not in total_json:
            total_json[key] = value
        else:
            total_json[key].update(value)
    return total_json

def edge_again(dot):
    global tryEdgeAgain
    again = []
    while len(tryEdgeAgain) > 0:
	edge = tryEdgeAgain.pop()
	if (existNode(edge['src']) and existNode(edge['dest'])):
	    dot.edge( edge['src'][3:], edge['dest'][3:], color = edge['color'], label = edge['label'] )
	else:
	    again.append(edge)
    tryEdgeAgain = again

def existNode(node):
    if node in map_nodes:
	return True
    else:
        return False

def signal_handler(signal, frame):
    with open('./python_camflow_graph.dot','w') as fil:
        fil.write(str(dot))
    with open('./python_camflow_graph.json','w') as fil:
        pprint(total_json,stream=fil,indent=2)
    print('Shutting down!')
    # dot.render('./provenance')

    sys.exit(0)

def matchFilter(label):
    # Sometimes camlfow filters do not work
    # So I put together this hack
    if (label.startswith("[envp]") || "lib/" in label || "/etc/" in label ||
        "cache" in label || ".so" in label || "cgroup" in label || "cmdline" in
        label || "[packet]" in label || "[address]" in label || "sudo" in label):
	return True
    else:
        return False
    
def insertNode(dot, key, label, color, shape):
    if (matchFilter(label)):
        return
    if(label is None):
	label = key
    map_nodes[key] = True
    dot.node( key[3:], fillcolor=color, shape=shape, label=label )

def insertEdge(dot, src, dest, label, color, check):
    if (existNode(src) and existNode(dest)):
	dot.edge( src[3:], dest[3:], color = color, label = label )
    else:
	tryEdgeAgain.append({'src': str(src), 'dest': str(dest), 'label': label, 'color': color})

def parse_entities(dot, entities):
    for key, dic in entities.items():
        label = ""
        if(dic.get('prov:label') is not None):
	    label = dic['prov:label']
	elif(dic.get('rdt:name') is not None):
	    label = dic['rdt:name']+' ['+dic['rdt:type']+']'
	else:
	    label = key
            
        if(entities[key]['prov:type']=='prov:agent'):
	    insertNode(dot, key, label, "blue", "circle");
	else:
	    insertNode(dot, key, label, "khaki1", "ellipse");

def parse_activities(dot, activities):
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
            
	insertNode(dot, key, label, "lightsteelblue1", "box")

def parse_agents(dot, agents):
    for key in agents:
	insertNode(dot, key, None, "blue", "cicrle")

def parse_edges(dot, eles, key1, key2, color, prelabel, check=""):
    for key,dic in eles.items():
	if dic.get('prov:label') is not None:
	   insertEdge(dot, str(dic[key1]), str(dic[key2]), prelabel +" - "+ dic['prov:label'], color, check)
	else:
	    insertEdge(dot, str(dic[key1]), str(dic[key2]), prelabel, color, check);
    
def parse_double_edges(dot, eles, key1, key2, neston, nest1, nest2):
    for key,dic in eles.items():
	insertEdge(dot, dic[key1], dic[key2], '#00CCCC', 'wasAssociatedWith');

def parse_nested_edges(dot, eles, key1, key2, neston, nest1, nest2):
    for key,dic in eles.items():
	insertEdge(dot, dic[key1], dic[key2], '#CC00CC', 'derivedByInsertionFrom')

def parse(json_msg, dot):
    parsed_json = json.loads(json_msg)
    global total_json
    total_json = combineDictVal(total_json,parsed_json)
    print("size of dictionary ", str(len(total_json)))
    lengths = [len(v) for v in total_json.values()]
    print(lengths)
    # TODO javascript code uses extend function here which I don't understand
    if parsed_json.get('entity') is not None:
        parse_entities(dot, parsed_json['entity'])
    if parsed_json.get('activity') is not None:
        parse_activities(dot, parsed_json['activity'])
    if parsed_json.get('agent') is not None:
        parse_agents(dot, parsed_json['agent'])
    edge_again(dot)
    
    if parsed_json.get('wasGeneratedBy') is not None:
        parse_edges(dot, parsed_json['wasGeneratedBy'], 'prov:entity', 'prov:activity', '#0000FF', 'wasGeneratedBy');

    if parsed_json.get('used') is not None:
        parse_edges(dot, parsed_json.get('used'), 'prov:activity', 'prov:entity', '#00FF00', 'used');

    if parsed_json.get('wasDerivedFrom') is not None:
        parse_edges(dot, parsed_json.get('wasDerivedFrom') , 'prov:generatedEntity', 'prov:usedEntity', '#FF9933', 'wasDerivedFrom', "now")

    if parsed_json.get('wasAttributedTo') is not None:
        parse_edges(dot, parsed_json.get('wasAttributedTo'), 'prov:entity', 'prov:agent', '#00CCCC', 'wasAttributedTo')
           
    if parsed_json.get('wasInformedBy') is not None:
        parse_edges(dot, parsed_json.get('wasInformedBy') , 'prov:informed', 'prov:informant', '#CC00CC', 'wasInformedBy')					

    if parsed_json.get('specializationOf') is not None:
        parse_edges(dot, parsed_json.get('specializationOf'), 'prov:entity', 'prov:secialization', '#CC00CC', 'specializationOf')
        
    if parsed_json.get('alternateOf') is not None:
        parse_edges(dot, parsed_json.get('alternateOf'), 'prov:entity', 'prov:alternae', '#CC00CC', 'alternateOf')

    if parsed_json.get('relation') is not None:
        parse_edges(dot, parsed_json.get('relation'), 'cf:receiver', 'cf:sender', '#FF0000', 'genericRelation')

    if parsed_json.get('wasAssociatedWith') is not None:
        parse_double_edges(dot, parsed_json.get('wasAssociatedWith') , 'prov:activity', 'prov:agent', 'prov:plan', 'prov:agent', 'prov:plan')

    if parsed_json.get('derivedByInsertionFrom') is not None:
        parse_nested_edges(dot, parsed_json.get('derivedByInsertionFrom') , 'prov:before','prov:after', 'prov:key-entity-set', 'prov:after','prov:key-entity-set')
        
    edge_again(dot)
           
def on_connect(client, userdata, flags, rc):
    print("Connected\n")

# The callback for when a message is received from the server.
def on_message(client, userdata, msg):
    # print(userdata)
    json_str = zlib.decompress(base64.b64decode(msg.payload))
    parse(json_str,userdata)
    
if __name__ == '__main__':
    TOPIC = "camflow/provenance/2098989664"
    # TOPIC = "camflow/provenance/1871596556"
    
    dot = Digraph('G',format='pdf')
    dot.graph_attr.update(ratio="fill")
    dot.node_attr.update(fontname="Helvetica-Bold",style="filled,setlinewidth(5)", margin="0.1,0.1",fontsize="40")
    dot.edge_attr.update(fontname="Helvetica-Bold", fontsize="40",weight="1",penwidth="8",arrowsize="2")
    
    client = mqtt.Client(userdata=dot)
    client.username_pw_set("kyekdxmk", "J6Y-kjN1-NbO")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("m12.cloudmqtt.com", 11724, 60)
    client.subscribe(TOPIC, qos=1)

    signal.signal(signal.SIGINT, signal_handler)
    client.loop_forever()
