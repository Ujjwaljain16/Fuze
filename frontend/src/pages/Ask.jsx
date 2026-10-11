import { MessageSquareText } from 'lucide-react'
import AskBookmarks from '../components/AskBookmarks'

const Ask = () => (
  <div className="min-h-screen text-white relative overflow-hidden" style={{ backgroundColor: '#0F0F1E' }}>
    <div className="relative z-10 w-full">
      <main className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto mt-12 md:mt-0">
        <div className="mb-6 md:mb-8 p-4 md:p-8 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl border border-gray-800 shadow-2xl">
          <div className="flex items-center gap-4 min-w-0">
            <div className="relative flex-shrink-0">
              <MessageSquareText className="w-7 h-7 md:w-8 md:h-8 text-cyan-400" />
              <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
            </div>
            <div className="min-w-0">
              <h1
                className="text-2xl md:text-4xl font-bold break-words"
                style={{
                  background: 'linear-gradient(to right, #4DD0E1, #14B8A6, #10B981)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  color: '#4DD0E1',
                }}
              >
                Ask your bookmarks
              </h1>
              <p className="text-gray-400 text-sm md:text-base mt-1">
                Answers written from your saved pages, with a citation for every claim.
              </p>
            </div>
          </div>
        </div>
        <AskBookmarks />
      </main>
    </div>
  </div>
)

export default Ask
