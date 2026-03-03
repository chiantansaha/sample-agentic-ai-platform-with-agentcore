import { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

interface ParsedContent {
  type: 'text' | 'thinking';
  content: string;
}

// <thinking>, <function_calls>, <function_result> 태그를 파싱하여 분리
// function_calls, function_result는 제거하고 (별도 UI로 표시), thinking만 표시
function parseSpecialBlocks(content: string): ParsedContent[] {
  const result: ParsedContent[] = [];

  // function_calls, function_result 태그는 제거 (message.tools로 별도 표시)
  let cleanedContent = content
    .replace(/<function_calls>[\s\S]*?<\/function_calls>/gi, '')
    .replace(/<function_result>[\s\S]*?<\/function_result>/gi, '');

  // thinking 태그 파싱
  const thinkingRegex = /<thinking>([\s\S]*?)<\/thinking>/gi;

  let lastIndex = 0;
  let match;

  while ((match = thinkingRegex.exec(cleanedContent)) !== null) {
    // 태그 이전 텍스트
    if (match.index > lastIndex) {
      const textBefore = cleanedContent.slice(lastIndex, match.index).trim();
      if (textBefore) {
        result.push({ type: 'text', content: textBefore });
      }
    }

    const tagContent = match[1].trim();
    if (tagContent) {
      result.push({ type: 'thinking', content: tagContent });
    }

    lastIndex = match.index + match[0].length;
  }

  // 나머지 텍스트
  if (lastIndex < cleanedContent.length) {
    const remaining = cleanedContent.slice(lastIndex).trim();
    if (remaining) {
      result.push({ type: 'text', content: remaining });
    }
  }

  // 태그가 없으면 전체 텍스트 반환
  if (result.length === 0 && cleanedContent.trim()) {
    result.push({ type: 'text', content: cleanedContent });
  }

  return result;
}

// Thinking 블록 컴포넌트
function ThinkingBlock({ content }: { content: string }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="my-2 border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center gap-2 text-left text-sm text-gray-500 hover:bg-gray-100 transition-colors"
      >
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-medium text-gray-600">Thinking</span>
        <span className="text-gray-400 text-xs">
          {isExpanded ? '(접기)' : '(펼치기)'}
        </span>
      </button>

      {isExpanded && (
        <div className="px-4 py-3 border-t border-gray-200 bg-white">
          <div className="text-sm text-gray-600 italic whitespace-pre-wrap leading-relaxed">
            {content}
          </div>
        </div>
      )}
    </div>
  );
}

export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  const parsedBlocks = useMemo(() => parseSpecialBlocks(content), [content]);

  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      {parsedBlocks.map((block, index) => {
        if (block.type === 'thinking') {
          return <ThinkingBlock key={index} content={block.content} />;
        }

        return (
          <ReactMarkdown
            key={index}
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              // 코드 블록 스타일링
              code: ({ node, inline, className, children, ...props }: any) => {
                return inline ? (
                  <code className="bg-gray-100 text-red-600 px-1 py-0.5 rounded text-sm" {...props}>
                    {children}
                  </code>
                ) : (
                  <code className={`${className} block bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto`} {...props}>
                    {children}
                  </code>
                );
              },
              // 링크 스타일링
              a: ({ node, children, ...props }: any) => (
                <a className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer" {...props}>
                  {children}
                </a>
              ),
              // 헤딩 스타일링
              h1: ({ node, children, ...props }: any) => (
                <h1 className="text-2xl font-bold text-gray-900 mt-6 mb-4" {...props}>
                  {children}
                </h1>
              ),
              h2: ({ node, children, ...props }: any) => (
                <h2 className="text-xl font-bold text-gray-900 mt-5 mb-3" {...props}>
                  {children}
                </h2>
              ),
              h3: ({ node, children, ...props }: any) => (
                <h3 className="text-lg font-semibold text-gray-900 mt-4 mb-2" {...props}>
                  {children}
                </h3>
              ),
              // 리스트 스타일링
              ul: ({ node, children, ...props }: any) => (
                <ul className="list-disc list-inside space-y-1 my-2" {...props}>
                  {children}
                </ul>
              ),
              ol: ({ node, children, ...props }: any) => (
                <ol className="list-decimal list-inside space-y-1 my-2" {...props}>
                  {children}
                </ol>
              ),
              // 인용구 스타일링
              blockquote: ({ node, children, ...props }: any) => (
                <blockquote className="border-l-4 border-gray-300 pl-4 italic text-gray-700 my-2" {...props}>
                  {children}
                </blockquote>
              ),
              // 테이블 스타일링
              table: ({ node, children, ...props }: any) => (
                <div className="overflow-x-auto my-4">
                  <table className="min-w-full border border-gray-300" {...props}>
                    {children}
                  </table>
                </div>
              ),
              th: ({ node, children, ...props }: any) => (
                <th className="border border-gray-300 bg-gray-100 px-4 py-2 text-left font-semibold" {...props}>
                  {children}
                </th>
              ),
              td: ({ node, children, ...props }: any) => (
                <td className="border border-gray-300 px-4 py-2" {...props}>
                  {children}
                </td>
              ),
              // 수평선
              hr: ({ node, ...props }: any) => (
                <hr className="my-4 border-gray-300" {...props} />
              ),
              // 단락
              p: ({ node, children, ...props }: any) => (
                <p className="my-2 leading-relaxed" {...props}>
                  {children}
                </p>
              ),
            }}
          >
            {block.content}
          </ReactMarkdown>
        );
      })}
    </div>
  );
}
