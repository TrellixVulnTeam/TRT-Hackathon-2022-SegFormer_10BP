import numpy as np
import onnx
import onnx_graphsurgeon as gs


# graph = gs.import_onnx(onnx.load("encoder_slice79.onnx"))
graph = gs.import_onnx(onnx.load("/root/onnx/segformer.b2.1024x1024.city.160k_v1.onnx"))
nLayerNormPlugin = 0
all_replace = 0
replace_idx = ['43', '54', '187', '320', '453', \
               '486', '497', '630', '763', '896', \
               '1029', '1062', '1073', '1206', '1339', \
               '1472', '1605', '1738', '1871', '2242',]

if all_replace:
    for node in graph.nodes:
        # replace layernorm
        if node.op == 'ReduceMean' and \
            node.o().op == 'Sub' and node.o().inputs[0] == node.inputs[0] and \
            node.o().o(0).op =='Pow' and node.o().o(1).op =='Div' and \
            node.o().o(0).o().op == 'ReduceMean' and \
            node.o().o(0).o().o().op == 'Add' and \
            node.o().o(0).o().o().o().op == 'Sqrt' and \
            node.o().o(0).o().o().o().o().op == 'Div' and node.o().o(0).o().o().o().o() == node.o().o(1):

            inputTensor = node.inputs[0]
            print(node.name)
            lastDivNode = node.o().o(0).o().o().o().o()

            layerNormN = gs.Node("LayerNorm", "LayerNormN-" + str(nLayerNormPlugin), inputs=[inputTensor], outputs=[lastDivNode.outputs[0]])
            graph.nodes.append(layerNormN)
            nLayerNormPlugin += 1

            lastDivNode.outputs = []

            continue   
else:
    for node in graph.nodes:
        # replace layernorm
        if node.op == 'ReduceMean' and node.name[11:] in replace_idx and \
            node.o().op == 'Sub' and node.o().inputs[0] == node.inputs[0] and \
            node.o().o(0).op =='Pow' and node.o().o(1).op =='Div' and \
            node.o().o(0).o().op == 'ReduceMean' and \
            node.o().o(0).o().o().op == 'Add' and \
            node.o().o(0).o().o().o().op == 'Sqrt' and \
            node.o().o(0).o().o().o().o().op == 'Div' and node.o().o(0).o().o().o().o() == node.o().o(1):

            inputTensor = node.inputs[0]
            print(node.name)
            lastDivNode = node.o().o(0).o().o().o().o()

            layerNormN = gs.Node("LayerNorm", "LayerNormN-" + str(nLayerNormPlugin), inputs=[inputTensor], outputs=[lastDivNode.outputs[0]])
            graph.nodes.append(layerNormN)
            nLayerNormPlugin += 1

            lastDivNode.outputs = []

            continue   
print(nLayerNormPlugin)
graph.cleanup().toposort()

onnx.save(gs.export_onnx(graph), "/root/onnx/segformer.b2.1024x1024.city.160k_replace_ln_v2.onnx")
print("pass")