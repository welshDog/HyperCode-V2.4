import ReactFlow, { 
  Controls, 
  Background, 
  BackgroundVariant,
  MiniMap,
  ReactFlowProvider,
  useReactFlow
} from 'reactflow';
import { useCallback, useRef } from 'react';
import 'reactflow/dist/style.css';
import { useFlowStore } from '../../store/flowStore';
import { CanvasBackground } from './CanvasBackground';
import { AgentNode } from './nodes/AgentNode';
import { AgentLibrary } from '../panels/AgentLibrary';
import { PropertiesPanel } from '../panels/PropertiesPanel';

const nodeTypes = {
  agent: AgentNode,
};

// Wrapper component to provide ReactFlow instance access
const HyperCanvasContent = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode } = useFlowStore();
  const { project } = useReactFlow();

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/hyperflow');
      if (!type) return;

      const agentData = JSON.parse(type);

      // check if the dropped element is valid
      if (typeof agentData === 'undefined' || !agentData) {
        return;
      }

      const position = reactFlowWrapper.current?.getBoundingClientRect();
      if (!position) return;

      const p = project({
        x: event.clientX - position.left,
        y: event.clientY - position.top,
      });

      const newNode = {
        id: `agent-${Date.now()}`,
        type: 'agent',
        position: p,
        data: { 
          ...agentData,
          status: 'idle',
          health: 100
        },
      };

      addNode(newNode);
    },
    [project, addNode]
  );

  return (
    <div className="w-full h-full flex">
      {/* Left Panel: Library */}
      <AgentLibrary />

      {/* Center: Canvas */}
      <div className="flex-1 relative bg-black" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDragOver={onDragOver}
          onDrop={onDrop}
          fitView
          snapToGrid
          snapGrid={[20, 20]}
          defaultEdgeOptions={{
            animated: true,
            style: { stroke: '#00F0FF', strokeWidth: 2 },
          }}
        >
          <CanvasBackground />
          
          <Controls style={{ 
            background: 'rgba(11, 4, 24, 0.8)', 
            border: '1px solid rgba(0, 243, 255, 0.2)',
            fill: '#00F0FF' 
          }} />
          
          <MiniMap 
            style={{ background: 'rgba(11, 4, 24, 0.9)', border: '1px solid rgba(0, 243, 255, 0.2)' }}
            nodeColor={() => '#00F0FF'}
            maskColor="rgba(0, 0, 0, 0.6)"
          />
        </ReactFlow>
      </div>

      {/* Right Panel: Properties */}
      <PropertiesPanel />
    </div>
  );
};

export const HyperCanvas = () => {
  return (
    <ReactFlowProvider>
      <HyperCanvasContent />
    </ReactFlowProvider>
  );
};
