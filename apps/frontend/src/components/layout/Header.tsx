import { Link } from 'react-router-dom';
import { Bot } from 'lucide-react';

export function Header() {
  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 h-16 flex items-center px-6">
      <div className="flex items-center justify-between w-full">
        {/* Logo and Title */}
        <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-700 rounded-lg">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            Agentic AI Platform
          </h1>
        </Link>
      </div>
    </header>
  );
}
