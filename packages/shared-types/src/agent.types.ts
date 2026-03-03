// Agent related types
export interface Agent {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive';
}
