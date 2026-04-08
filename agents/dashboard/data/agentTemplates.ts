// Agent Templates Configuration
export const AGENT_TEMPLATES = [
  { 
    role: 'frontend',   
    avatar: '🎨', 
    name: 'Frontend Ace',
    tools: ['react', 'css', 'nextjs'],        
    color: '#00F0FF',
    description: 'Specializes in UI/UX and component architecture.'
  },
  { 
    role: 'backend',    
    avatar: '⚙️', 
    name: 'Backend Beast',
    tools: ['fastapi', 'postgres', 'redis'],  
    color: '#00FF9D',
    description: 'Handles API logic, database schemas, and performance.'
  },
  { 
    role: 'qa',         
    avatar: '🧪', 
    name: 'QA Ninja',
    tools: ['pytest', 'playwright'],          
    color: '#FF9F43',
    description: 'Ensures code quality through automated testing.'
  },
  { 
    role: 'devops',     
    avatar: '🚀', 
    name: 'DevOps Wizard',
    tools: ['docker', 'k8s', 'ci-cd'],        
    color: '#9D00FF',
    description: 'Manages deployment pipelines and infrastructure.'
  },
  { 
    role: 'security',   
    avatar: '🛡️', 
    name: 'Security Guard',
    tools: ['audit', 'scan', 'shield'],       
    color: '#FF3366',
    description: 'Audits code for vulnerabilities and security flaws.'
  },
  { 
    role: 'architect',  
    avatar: '🏗️', 
    name: 'Sys Architect',
    tools: ['design', 'review', 'plan'],      
    color: '#FFD700',
    description: 'Designs high-level system architecture and patterns.'
  },
  { 
    role: 'strategist', 
    avatar: '🎯', 
    name: 'Project Boss',
    tools: ['roadmap', 'prioritize'],         
    color: '#00F0FF',
    description: 'Defines clear project roadmap and prioritizes features.'
  },
  { 
    role: 'healer',     
    avatar: '❤️', 
    name: 'Healer Agent',
    tools: ['monitor', 'recover', 'restart'], 
    color: '#00FF9D',
    description: 'Monitors system health and attempts auto-recovery.'
  },
  { 
    role: 'tips-tricks', 
    avatar: '💡', 
    name: 'Tips Architect',
    tools: ['write', 'neuro-ux', 'chunk'],         
    color: '#FFD700',
    description: 'Generates neurodivergent-friendly development guides.'
  }
];
