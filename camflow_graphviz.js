//var $ = require('jQuery');
const Paho = require('./paho-node/mqttws31.js')
const URL = 'm12.cloudmqtt.com'
const PORT = 31724
const TOPIC = 'camflow/provenance/2098989664'
var client;
var util = require('util'), graphviz = require('graphviz');
var pako = require('pako');
var atob = require('atob');
var parseJson = require('parse-json');
//var $ = require('jQuery');

var g = graphviz.digraph("G");
var fs = require('fs');
var agent_c = "blue";
var entity_c = "red";
var activity_c = "green"
var agent_s = "circle";
var entity_s = "square";
var activity_s = "diamond"

var final_json = "";
var tryEdgeAgain = new Array();
var total_act = 0;
var total_ent = 0;
var filter_nodes = [];

var map = {}

process.on( "SIGINT", function() {
    //var dot_graph = g.to_dot()
    dotfile.write(g.to_dot())
    dotfile.end()
    jsonfile.write(final_json)
    jsonfile.end()
    console.log('CLOSING [SIGINT]');
    console.log('total act ' + total_act)
    console.log('total ent ' + total_ent)
    console.log('Unmatched edge :'+tryEdgeAgain.length);
    process.exit();
} );

// Array.prototype.pushArray = function() {
//     this.push.apply(this, this.concat.apply([], arguments));
// };

/* convert from B64 to byteArray 
   function obtained from cytoscape-prov-mqtt.js
*/
function inflateB64(str){
    var byteCharacters = atob(str);
    var byteNumbers = new Array(byteCharacters.length);
    for (var i = 0; i < byteCharacters.length; i++) {
	byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    var byteArray = new Uint8Array(byteNumbers);
    /* decompress */

    var data = pako.inflate(byteArray);
    var strData = String.fromCharCode.apply(null, new Uint16Array(data));
    return strData;
}

function edge_again(){
    var edge;
    var again = new Array();
    while(tryEdgeAgain.length>0){
	edge = tryEdgeAgain.pop();
	if (existNode(edge.src) && existNode(edge.dest)){
	    var e = g.addEdge( edge.src, edge.dest );
	    e.set("label", edge.label);
	    e.set( "color", edge.color);
	}
	else
	    again.push(edge)
    }
    tryEdgeAgain = again;

}

/*function from online source that replaces jquery extend function*/
function extending(a, b, c){
    for(var key in b)
	if(b.hasOwnProperty(key))
	    a[key] = b[key];
    for(var key in c)
	if(c.hasOwnProperty(key))
	    a[key] = c[key];
    return a;
}

function existNode(node){
    if (node in map)

	return true
    else return false
}

function insertNode(id, label, color, shape){

    if (label.startsWith("[envp]")){
	filter_nodes.add(id);
	return;
    }
    if(typeof label === 'undefined')
	label = id;
    //if (typeof superNode === 'undefined')
    map[id] = "true";
    var n1 = g.addNode( id, {"color" : color, "shape": shape, "label":label} );
}

function parse_entities(entities){
    for(var key in entities){
	total_ent += 1
	//console.log("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!~~~~~~~~~~~~~~")
	//console.log(key)
	//console.log(entities[key])
	var parent_id = undefined;
	if(entities[key]['prov:label']!=undefined){
	    var label = entities[key]['prov:label'];
	} else if(entities[key]['rdt:name']!=undefined){
	    var label = entities[key]['rdt:name']+' ['+entities[key]['rdt:type']+']';
	}else{
	    var label = key;
	}

	// // remove this portion for a while coz 1. the jsons that we have dont have parent and
	// // 2. difficult to understand
	// if(entities[key]['cf:hasParent'] != undefined){
	// 	parent_id = entities[key]['cf:hasParent'];
	// 	if(cy.elements('node[id="'+parent_id+'"]').empty()){ // parent does not exist yet
	// 		tryNodeAgain.push({fn: cy.prov_core().entity, json: entities[key], key: key, label: label, parent_id: parent_id});
	// 		continue;
	// 	}
	// }else	


	// not sure what this does
	// if(entities[key]['prov:type'] != undefined
	// 	&& entities[key]['cf:id']!=undefined
	// 	&& entities[key]['cf:seq'] == undefined){
	// 		var parent_label = entities[key]['cf:id'];
	// 		// mana letak parent id?
	// 		var parent_id = entities[key]['prov:type'].toString() + entities[key]['cf:id'].toString() + entities[key]['cf:boot_id'].toString() + entities[key]['cf:machine_id'].toString();
	// 		console.log("inserting " + parent_label)
	// 		insertNode(parent_id, parent_label, entity_c, entity_s);
	// }else if(entities[key]['cf:machine_id'] != undefined){
	// 	var parent_id = entities[key]['cf:machine_id'];
	// }

	if(entities[key]['prov:type']=='prov:agent'){
	    insertNode(key, label, agent_c, agent_s);
	    //console.log("inserting " + label)
	}else{
	    insertNode(key, label, entity_c, entity_s);
	    //console.log("inserting " + label)
	}
    }
}

function parse_activities(activities){
    for(var key in activities){
	console.log("*****")
	console.log(activities)
	console.log("*****")
	total_act += 1
	var parent_id = undefined;

	if(activities[key]['prov:label']!=undefined){
	    var label = activities[key]['prov:label'];
	} else if(activities[key]['rdt:name']!=undefined){
	    if(activities[key]['rdt:startLine']!='NA'){
		var label = activities[key]['rdt:name']+' ['+activities[key]['rdt:type']+'](Line: '+activities[key]['rdt:startLine']+')';
	    }else{
		var label = activities[key]['rdt:name']+' ['+activities[key]['rdt:type']+']';
	    }
	}else{
	    var label = key;
	}

	// if(activities[key]['cf:hasParent'] != undefined){
	//     parent_id = activities[key]['cf:hasParent'];
	//     if(cy.elements('node[id="'+parent_id+'"]').empty()){ // parent does not exist yet
	// 	tryNodeAgain.push({fn: cy.prov_core().activity, json: activities[key], key: key, label: label, parent_id: parent_id});
	// 	continue;
	//     }
	// }else	if(activities[key]['prov:type'] != undefined && activities[key]['cf:id'] != undefined){
	//     var parent_label = activities[key]['cf:id'];
	//     parent_id = activities[key]['prov:type'].toString() + activities[key]['cf:id'].toString() + activities[key]['cf:boot_id'].toString() + activities[key]['cf:machine_id'].toString();
	//     insertNode(parent_id, parent_label, activity_c, activity_s);
	// }
	
	// if (activities[key]['cf:secctx'] != undefined){
	//     label = label + "\n" + activities[key]['cf:secctx']
	// }
	// if (activities[key]['docker'] != undefined){
	//     label = label + "\n" + activities[key]['docker']
	// }
	if (activities[key]['cf:pid'] != undefined){
	    label = label + "\n PID=" + activities[key]['cf:pid']
	}
	if (activities[key]['cf:vpid'] != undefined){
	    label = label + "\n VPID=" + activities[key]['cf:vpid']
	}
	if (activities[key]['cf:uid'] != undefined){
	    label = label + "\n UID=" + activities[key]['cf:uid']
	}
	if (activities[key]['cf:tgid'] != undefined){
	    label = label + "\n TGID=" + activities[key]['cf:tgid']
	}
	insertNode(key, label, activity_c, activity_s);
    }
}

function parse_agents(agents){
    for(var key in agents){
	insertNode( key, undefined, agent_c, agent_s);
    }
}

function insertEdge(src, dest, label, color, check){

    if (existNode(src) && existNode(dest)){
	var e = g.addEdge( src, dest );
	e.set("label", label);
	e.set( "color", color);
    }
    else{
	tryEdgeAgain.push({src: src, dest: dest, label: label, color: color});
    }
}

function parse_edges(eles, key1, key2, color, prelabel, check){
    for(var key in eles){
	// if(missing(fn, eles[key][key1], eles[key][key2]))
	// 	continue;
	if(eles[key]['prov:label']!=undefined){
	    insertEdge(eles[key][key1], eles[key][key2], prelabel +" - "+ eles[key]['prov:label'], color, check);
	}else{
	    insertEdge(eles[key][key1], eles[key][key2], prelabel, color, check);
	}
    }
}

function parse_double_edges(eles, key1, key2, neston, nest1, nest2){
    // removed parts of function that i dont know (yet) how to deal with 
    for(var key in eles){
	insertEdge(eles[key][key1], eles[key][key2], '#00CCCC', 'wasAssociatedWith');
    }
}

function parse_nested_edges(eles, key1, key2, neston, nest1, nest2){
    for(var key in eles){
	insertEdge(eles[key][key1], eles[key][key2], '#CC00CC', 'derivedByInsertionFrom');
    }
}

function parse(json){
    final_json = final_json + json
    // console.log(json);
    try {
	var h=parseJson(json);
    } catch (err) {
	console.log("error in parsing");
	throw err;
    }
    //var data = JSON.parse(text);
    //console.log(h);
    var tmp = {};
    // $.extend(true, tmp, json, data);
    tmp2 = extending(tmp, json, h);
    json = tmp2;
    parse_entities(h.entity);
    parse_activities(h.activity);
    parse_agents(h.agent);

    //parse_messages(h.message);

    //	try nodes that could not be inserted earlier
    //node_again();
    //	try edges that could not be inserted earlier
    edge_again();

    parse_edges(h.wasGeneratedBy, 'prov:entity', 'prov:activity', '#0000FF', 'wasGeneratedBy');

    parse_edges(h.used, 'prov:activity', 'prov:entity', '#00FF00', 'used');

    parse_edges(h.wasDerivedFrom, 'prov:generatedEntity', 'prov:usedEntity', '#FF9933', 'wasDerivedFrom', "now")

    parse_edges(h.wasAttributedTo, 'prov:entity', 'prov:agent', '#00CCCC', 'wasAttributedTo')					

    // have to flip the src and target coz the cytoscape api have inverted source and dest
    parse_edges(h.wasInformedBy, 'prov:informed', 'prov:informant', '#CC00CC', 'wasInformedBy')					

    parse_edges(h.specializationOf, 'prov:entity', 'prov:secialization', '#CC00CC', 'specializationOf')
    parse_edges(h.alternateOf, 'prov:entity', 'prov:alternae', '#CC00CC', 'alternateOf')
    parse_edges(h.relation, 'cf:receiver', 'cf:sender', '#FF0000', 'genericRelation')

    parse_double_edges(h.wasAssociatedWith,
		       //cy.prov_core().wasAssociatedWith,
		       'prov:activity',
		       'prov:agent',
		       'prov:plan',
		       //cy.prov_core().hadPlan,
		       'prov:agent',
		       'prov:plan');


    parse_nested_edges(h.derivedByInsertionFrom,
		       //cy.prov_core().derivedByInsertionFrom,
		       'prov:before',
		       'prov:after',
		       'prov:key-entity-set',
		       //cy.prov_core().hadDictionaryMember,
		       'prov:after',
		       'prov:key-entity-set');

    //if (generate_dot)
    console.log(g);
    g.output( "pdf", "graphviz.pdf" );
    console.log("done");
}

// called when a message arrives
function onMessageArrived(message) {
    console.log("New message \n")
    var json = inflateB64(message.payloadString);
    parse(json);
}

function onFailure(invocationContext, errorCode, errorMessage) {
    console.log("Failed to connect!");
}

// called when the client connects
function onConnect() {
    // Once a connection has been made, make a subscription and send a message.
    console.log("Connected!");
    client.subscribe(TOPIC);
}

// var myArgs = process.argv.slice(2);
// console.log('myArgs: ', myArgs);

// switch (myArgs[0]) {
// case 'file':
//     var text = fs.readFileSync('camflow_graph.json','utf8');
//     // console.log (text);
//     console.log('parsing****');
//     var jsonPretty = JSON.stringify(JSON.parse(text),null,2);
//     console.log(jsonPretty)
//     parse(text);
//     break;
// case 'mqtt':
var dotfile = fs.createWriteStream('camflow_graph.dot', {
    flags: 'w' // 'a' means appending (old data will be preserved)
})
var jsonfile = fs.createWriteStream('camflow_graph.json', {
    flags: 'w' // 'a' means appending (old data will be preserved)
})
// connect to mqtt
client = new Paho.MQTT.Client(URL, PORT, "/", 'ws' + Math.random());
// set callback handlers
client.onMessageArrived = onMessageArrived;
client.connect({
    useSSL: true,
    userName: 'kyekdxmk',
    password: 'J6Y-kjN1-NbO',
    onSuccess: onConnect,
    onFailure: onFailure
});


//     break;
// default:
//     console.log('Sorry, that is not something I know how to do.');
// }

