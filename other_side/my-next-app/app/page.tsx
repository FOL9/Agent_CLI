"use client";

import React from 'react';
import { 
  ArrowRight, 
  Layers, 
  Zap, 
  Shield, 
  Globe, 
  Star,
  CheckCircle,
  Github,
  Twitter,
  Linkedin,
  Command,
  MousePointer2,
  Sparkles
} from "lucide-react";
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-indigo-500/30 selection:text-indigo-200 font-sans">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-black/60 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 group cursor-pointer" onClick={() => window.scrollTo({top: 0, behavior: 'smooth'})}>
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center group-hover:rotate-6 transition-transform">
              <Sparkles className="text-white w-5 h-5 fill-current" />
            </div>
            <span className="font-bold text-xl tracking-tight">Lumina</span>
          </div>
          
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
            <Link href="/plan" className="hover:text-white transition-colors">Planner</Link>
          </div>

          <div className="flex items-center gap-4">
            <button className="hidden sm:block text-sm font-medium text-zinc-400 hover:text-white transition-colors">
              Sign in
            </button>
            <Link 
              href="/plan"
              className="text-sm font-semibold bg-white text-black px-5 py-2 rounded-full hover:bg-zinc-200 transition-all active:scale-95"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <main>
        {/* Hero Section */}
        <section className="relative pt-32 pb-20 overflow-hidden">
          {/* Ambient Background */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-[radial-gradient(circle_at_50%_-20%,#312e81,transparent_70%)] -z-10 opacity-50"></div>
          
          <div className="max-w-7xl mx-auto px-6 text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 text-xs font-medium mb-8">
              <span className="flex h-2 w-2 rounded-full bg-indigo-500"></span>
              Lumina Planner v2.0 is now live
            </div>
            
            <h1 className="text-5xl md:text-8xl font-bold tracking-tighter mb-8 bg-gradient-to-b from-white to-zinc-500 bg-clip-text text-transparent">
              Organize at the speed <br /> of imagination.
            </h1>
            
            <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              The intelligent planner built for modern high-performers. 
              Manage your day with Lumina's lightning-fast interface and AI-inspired workflow.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              <Link 
                href="/plan"
                className="group flex items-center gap-2 bg-indigo-600 text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-indigo-500 transition-all shadow-[0_0_20px_rgba(79,70,229,0.4)]"
              >
                Start planning for free
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <button className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 px-8 py-4 rounded-full font-bold text-lg hover:bg-zinc-800 transition-all">
                Watch Demo
              </button>
            </div>

            {/* Dashboard Preview Placeholder */}
            <div className="relative max-w-5xl mx-auto mt-12">
               <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl blur opacity-20"></div>
               <div className="relative bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl aspect-video flex items-center justify-center group">
                  <div className="text-center">
                    <div className="w-20 h-20 bg-indigo-600/10 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform">
                      <Sparkles className="w-10 h-10 text-indigo-500" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2">Interactive AI Planner</h3>
                    <p className="text-zinc-500 mb-8">Click below to experience the future of productivity.</p>
                    <Link href="/plan" className="px-6 py-3 bg-white text-black rounded-full font-bold hover:bg-zinc-200 transition-all">
                      Open Planner
                    </Link>
                  </div>
               </div>
            </div>
          </div>
        </section>

        {/* Social Proof */}
        <section className="py-20 border-y border-white/5 bg-zinc-950/50">
          <div className="max-w-7xl mx-auto px-6">
            <p className="text-center text-zinc-500 text-sm font-medium mb-10 uppercase tracking-widest">Loved by productive teams everywhere</p>
            <div className="flex flex-wrap justify-center gap-12 md:gap-24 opacity-50 grayscale hover:grayscale-0 transition-all">
               {['Vercel', 'Stripe', 'Linear', 'Supabase', 'Raycast'].map((brand) => (
                 <span key={brand} className="text-2xl font-bold tracking-tighter text-zinc-300">{brand}</span>
               ))}
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-32 px-6">
          <div className="max-w-7xl mx-auto">
            <div className="max-w-2xl mb-20">
              <h2 className="text-indigo-500 font-semibold mb-4">Powerful Planning</h2>
              <h3 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">Everything you need to master your time.</h3>
              <p className="text-zinc-400 text-lg">Lumina combines task management, priority tracking, and focus modes into one seamless experience.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  title: "Smart Categorization",
                  desc: "Automatically group your tasks by project, priority, or due date.",
                  icon: <Layers className="w-6 h-6" />,
                },
                {
                  title: "Lightning Fast",
                  desc: "Keyboard-first interface designed for speed. Add tasks in milliseconds.",
                  icon: <Zap className="w-6 h-6" />,
                },
                {
                  title: "Private & Secure",
                  desc: "Your data is stored locally and encrypted. We never see your personal tasks.",
                  icon: <Shield className="w-6 h-6" />,
                },
                {
                  title: "Cloud Sync",
                  desc: "Sync your tasks across all your devices in real-time with end-to-end encryption.",
                  icon: <Globe className="w-6 h-6" />,
                },
                {
                  title: "Quick Commands",
                  desc: "Use the command palette to quickly navigate and manage your planner.",
                  icon: <Command className="w-6 h-6" />,
                },
                {
                  title: "Intuitive Design",
                  desc: "A beautiful, minimal interface that stays out of your way so you can focus.",
                  icon: <MousePointer2 className="w-6 h-6" />,
                }
              ].map((f, i) => (
                <div key={i} className="p-8 rounded-2xl bg-zinc-900/50 border border-zinc-800 hover:bg-zinc-900 transition-colors group">
                  <div className="w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center mb-6 text-indigo-500 group-hover:scale-110 transition-transform">
                    {f.icon}
                  </div>
                  <h4 className="text-xl font-bold mb-3">{f.title}</h4>
                  <p className="text-zinc-400 leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Testimonial */}
        <section className="py-32 px-6 bg-indigo-600">
           <div className="max-w-4xl mx-auto text-center">
              <div className="flex justify-center gap-1 mb-8">
                {[...Array(5)].map((_, i) => <Star key={i} className="w-6 h-6 fill-current text-white" />)}
              </div>
              <blockquote className="text-3xl md:text-5xl font-bold text-white mb-10 tracking-tight leading-tight">
                "Lumina has completely transformed how I manage my day. It's faster, smarter, and more intuitive than any other planner I've used."
              </blockquote>
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 rounded-full bg-indigo-400 mb-4 overflow-hidden border-2 border-white/20">
                  <div className="w-full h-full bg-zinc-800 animate-pulse"></div>
                </div>
                <p className="font-bold text-lg">Alex Rivera</p>
                <p className="text-indigo-200">Product Manager, FlowState</p>
              </div>
           </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="py-32 px-6">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-20">
              <h2 className="text-4xl md:text-5xl font-bold mb-6">Simple Pricing</h2>
              <p className="text-zinc-400 text-lg">Choose the plan that fits your productivity needs.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {/* Free */}
              <div className="p-8 rounded-2xl bg-zinc-950 border border-zinc-800 flex flex-col">
                <h3 className="text-xl font-bold mb-2">Personal</h3>
                <div className="text-4xl font-bold mb-6">$0</div>
                <ul className="space-y-4 mb-8 flex-grow">
                  {['Unlimited Tasks', 'Local Storage', 'Basic Filters'].map(item => (
                    <li key={item} className="flex items-center gap-3 text-zinc-400 text-sm">
                      <CheckCircle className="w-4 h-4 text-indigo-500" /> {item}
                    </li>
                  ))}
                </ul>
                <Link 
                  href="/plan"
                  className="w-full py-3 rounded-lg border border-zinc-800 hover:bg-zinc-900 transition-colors font-semibold text-center"
                >
                  Get Started
                </Link>
              </div>

              {/* Pro */}
              <div className="p-8 rounded-2xl bg-indigo-600 border border-indigo-500 flex flex-col shadow-xl shadow-indigo-500/20 transform md:scale-105">
                <h3 className="text-xl font-bold mb-2 text-white">Pro</h3>
                <div className="text-4xl font-bold mb-6 text-white">$9<span className="text-lg font-normal text-indigo-200">/mo</span></div>
                <ul className="space-y-4 mb-8 flex-grow">
                  {['Cloud Sync', 'AI Task Suggestions', 'Priority Support', 'Custom Themes'].map(item => (
                    <li key={item} className="flex items-center gap-3 text-indigo-100 text-sm">
                      <CheckCircle className="w-4 h-4 text-white" /> {item}
                    </li>
                  ))}
                </ul>
                <button className="w-full py-3 rounded-lg bg-white text-indigo-600 hover:bg-zinc-100 transition-colors font-bold">Try Pro for Free</button>
              </div>

              {/* Enterprise */}
              <div className="p-8 rounded-2xl bg-zinc-950 border border-zinc-800 flex flex-col">
                <h3 className="text-xl font-bold mb-2">Teams</h3>
                <div className="text-4xl font-bold mb-6">Custom</div>
                <ul className="space-y-4 mb-8 flex-grow">
                  {['Shared Lists', 'Team Analytics', 'Dedicated Support', 'Admin Console'].map(item => (
                    <li key={item} className="flex items-center gap-3 text-zinc-400 text-sm">
                      <CheckCircle className="w-4 h-4 text-indigo-500" /> {item}
                    </li>
                  ))}
                </ul>
                <button className="w-full py-3 rounded-lg border border-zinc-800 hover:bg-zinc-900 transition-colors font-semibold">Contact Sales</button>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 px-6">
          <div className="max-w-5xl mx-auto rounded-3xl bg-zinc-900 border border-zinc-800 p-12 text-center relative overflow-hidden">
             <div className="absolute top-0 right-0 -mt-20 -mr-20 w-64 h-64 bg-indigo-600/20 blur-[100px] rounded-full"></div>
             <div className="absolute bottom-0 left-0 -mb-20 -ml-20 w-64 h-64 bg-purple-600/20 blur-[100px] rounded-full"></div>
             
             <h2 className="text-4xl md:text-5xl font-bold mb-6 relative z-10">Ready to master your day?</h2>
             <p className="text-zinc-400 text-lg mb-10 max-w-2xl mx-auto relative z-10">Join over 50,000 high-performers who use Lumina to stay organized and productive.</p>
             <Link 
               href="/plan"
               className="bg-white text-black px-10 py-4 rounded-full font-bold text-lg hover:bg-zinc-200 transition-all relative z-10"
             >
               Get Started for Free
             </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="py-20 px-6 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-12 mb-20">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-6 h-6 bg-indigo-600 rounded flex items-center justify-center">
                  <Sparkles className="text-white w-4 h-4 fill-current" />
                </div>
                <span className="font-bold text-lg">Lumina</span>
              </div>
              <p className="text-zinc-500 text-sm max-w-xs mb-8">
                The next generation planner for modern high-performers.
              </p>
              <div className="flex gap-4">
                <Twitter className="w-5 h-5 text-zinc-500 hover:text-white cursor-pointer transition-colors" />
                <Github className="w-5 h-5 text-zinc-500 hover:text-white cursor-pointer transition-colors" />
                <Linkedin className="w-5 h-5 text-zinc-500 hover:text-white cursor-pointer transition-colors" />
              </div>
            </div>
            
            <div>
              <h4 className="font-bold mb-6 text-sm text-zinc-200">Product</h4>
              <ul className="space-y-4 text-sm text-zinc-500">
                <li><a href="#" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Integrations</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Changelog</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold mb-6 text-sm text-zinc-200">Resources</h4>
              <ul className="space-y-4 text-sm text-zinc-500">
                <li><a href="#" className="hover:text-white transition-colors">Documentation</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Help Center</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Community</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Templates</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold mb-6 text-sm text-zinc-200">Company</h4>
              <ul className="space-y-4 text-sm text-zinc-500">
                <li><a href="#" className="hover:text-white transition-colors">About</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Privacy</a></li>
              </ul>
            </div>
          </div>
          
          <div className="pt-8 border-t border-white/5 text-sm text-zinc-500 flex flex-col md:flex-row justify-between items-center gap-4">
            <p>© 2024 Lumina Labs Inc. All rights reserved.</p>
            <div className="flex gap-8">
              <a href="#" className="hover:text-white transition-colors">Terms</a>
              <a href="#" className="hover:text-white transition-colors">Privacy</a>
              <a href="#" className="hover:text-white transition-colors">Cookies</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
