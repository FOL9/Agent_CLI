import Planner from '@/components/Planner';
import { Sparkles } from 'lucide-react';
import Link from 'next/link';

export default function PlanPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-indigo-500/30 selection:text-indigo-200 font-sans">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-black/60 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group cursor-pointer">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center group-hover:rotate-6 transition-transform">
              <Sparkles className="text-white w-5 h-5 fill-current" />
            </div>
            <span className="font-bold text-xl tracking-tight">Lumina</span>
          </Link>
          
          <div className="flex items-center gap-4">
            <Link href="/" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
              Back to Home
            </Link>
          </div>
        </div>
      </nav>

      <main className="pt-24 pb-20">
        <div className="max-w-7xl mx-auto px-6">
          <Planner />
        </div>
      </main>
    </div>
  );
}
