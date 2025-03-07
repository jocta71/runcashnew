
export interface ChatMessage {
  id: number;
  sender: string;
  message: string;
  isAdmin?: boolean;
  isModerator?: boolean;
  avatar?: string;
  timestamp: Date;
}
