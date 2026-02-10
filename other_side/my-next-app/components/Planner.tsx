"use client";

import React, { useState, useEffect, useRef } from 'react';
import { 
  Plus, 
  Trash2, 
  CheckCircle2, 
  Circle, 
  Calendar, 
  Tag, 
  AlertCircle,
  Search,
  Filter,
  MoreVertical,
  ChevronRight,
  Clock,
  X,
  Edit3,
  Flag,
  ChevronDown,
  BarChart3,
  Wand2,
  Loader2
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import Chat from './Chat';

type Priority = 'low' | 'medium' | 'high';

interface Task {
  id: string;
  title: string;
  completed: boolean;
  priority: Priority;
  category: string;
  dueDate?: string;
  createdAt: number;
}

const CATEGORIES = ['General', 'Work', 'Personal', 'Shopping', 'Health', 'Finance'];
const PRIORITIES: { value: Priority; label: string; color: string }[] = [
  { value: 'low', label: 'Low', color: 'text-emerald-500 bg-emerald-500/10' },
  { value: 'medium', label: 'Medium', color: 'text-amber-500 bg-amber-500/10' },
  { value: 'high', label: 'High', color: 'text-rose-500 bg-rose-500/10' },
];

export default function Planner() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState<Priority>('medium');
  const [newTaskCategory, setNewTaskCategory] = useState('General');
  const [newTaskDueDate, setNewTaskDueDate] = useState('');
  
  const [isAdding, setIsAdding] = useState(false);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [showStats, setShowStats] = useState(false);
  const [sortBy, setSortBy] = useState<'newest' | 'priority' | 'dueDate'>('newest');
  const [isGenerating, setIsGenerating] = useState(false);

  const formRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (e.key === 'n' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        setIsAdding(true);
      }
      if (e.key === 'Escape') {
        setIsAdding(false);
        setEditingTaskId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
  useEffect(() => {
    const savedTasks = localStorage.getItem('lumina-tasks');
    if (savedTasks) {
      try {
        setTasks(JSON.parse(savedTasks));
      } catch (e) {
        console.error("Failed to load tasks", e);
      }
    }
  }, []);

  // Save tasks to localStorage
  useEffect(() => {
    localStorage.setItem('lumina-tasks', JSON.stringify(tasks));
  }, [tasks]);

  const addTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    const newTask: Task = {
      id: Math.random().toString(36).substring(2, 9),
      title: newTaskTitle,
      completed: false,
      priority: newTaskPriority,
      category: newTaskCategory,
      dueDate: newTaskDueDate || undefined,
      createdAt: Date.now(),
    };

    setTasks([newTask, ...tasks]);
    setNewTaskTitle('');
    setNewTaskPriority('medium');
    setNewTaskCategory('General');
    setNewTaskDueDate('');
    setIsAdding(false);
  };

  const toggleTask = (id: string) => {
    setTasks(tasks.map(task => 
      task.id === id ? { ...task, completed: !task.completed } : task
    ));
  };

  const deleteTask = (id: string) => {
    setTasks(tasks.filter(task => task.id !== id));
  };

  const startEditing = (task: Task) => {
    setEditingTaskId(task.id);
    setEditTitle(task.title);
  };

  const saveEdit = (id: string) => {
    setTasks(tasks.map(task => 
      task.id === id ? { ...task, title: editTitle } : task
    ));
    setEditingTaskId(null);
  };

  const generateAIPlan = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch('/api/ai-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tasks }),
      });
      const data = await response.json();
      if (data.suggestedTasks) {
        const newTasks: Task[] = data.suggestedTasks.map((t: any) => ({
          id: Math.random().toString(36).substring(2, 9),
          title: t.title,
          completed: false,
          priority: t.priority || 'medium',
          category: t.category || 'General',
          createdAt: Date.now(),
        }));
        setTasks([...newTasks, ...tasks]);
      }
    } catch (error) {
      console.error("AI Generation failed", error);
    } finally {
      setIsGenerating(false);
    }
  };

  const addSuggestedTasks = (suggestedTasks: any[]) => {
    const newTasks: Task[] = suggestedTasks.map((t: any) => ({
      id: Math.random().toString(36).substring(2, 9),
      title: t.title,
      completed: false,
      priority: t.priority || 'medium',
      category: t.category || 'General',
      createdAt: Date.now(),
    }));
    setTasks(prev => [...newTasks, ...prev]);
  };

  const filteredTasks = tasks.filter(task => {
    const matchesFilter = 
      filter === 'all' ? true :
      filter === 'active' ? !task.completed :
      task.completed;
    
    const matchesCategory = categoryFilter === 'All' || task.category === categoryFilter;
    const matchesSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase());
    
    return matchesFilter && matchesCategory && matchesSearch;
  }).sort((a, b) => {
    if (sortBy === 'newest') return b.createdAt - a.createdAt;
    if (sortBy === 'priority') {
      const priorityMap = { high: 3, medium: 2, low: 1 };
      return priorityMap[b.priority] - priorityMap[a.priority];
    }
    if (sortBy === 'dueDate') {
      if (!a.dueDate) return 1;
      if (!b.dueDate) return -1;
      return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
    }
    return 0;
  });

  const getPriorityColor = (priority: Priority) => {
    return PRIORITIES.find(p => p.value === priority)?.color || 'text-zinc-500 bg-zinc-500/10';
  };

  const stats = {
    total: tasks.length,
    completed: tasks.filter(t => t.completed).length,
    active: tasks.filter(t => !t.completed).length,
    highPriority: tasks.filter(t => t.priority === 'high' && !t.completed).length,
  };

  const completionRate = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8">
      <header className="mb-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-2">My Planner</h1>
            <p className="text-zinc-400">Manage your tasks and stay productive.</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2 text-sm font-medium text-zinc-400 bg-zinc-900/50 px-3 py-1.5 rounded-full border-zinc-800">
              <Clock className="w-4 h-4" />
              {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </div>
            <div className="flex items-center gap-4">
              <button 
                onClick={generateAIPlan}
                disabled={isGenerating}
                className="flex items-center gap-2 text-xs font-bold text-indigo-400 hover:text-indigo-300 transition-colors disabled:opacity-50"
              >
                {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
                {isGenerating ? 'Generating...' : 'AI Planner'}
              </button>
              <button 
                onClick={() => setShowStats(!showStats)}
                className="flex items-center gap-2 text-xs font-bold text-zinc-500 hover:text-zinc-400 transition-colors"
              >
                <BarChart3 className="w-3.5 h-3.5" />
                {showStats ? 'Hide Stats' : 'Show Stats'}
              </button>
            </div>
          </div>
        </div>

        <AnimatePresence>
          {showStats && (
            <motion.div 
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden mb-8"
            >
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 bg-zinc-900/50 rounded-3xl">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Completion</p>
                  <p className="text-2xl font-bold text-white">{completionRate}%</p>
                  <div className="w-full h-1.5 bg-zinc-800 rounded-full mt-2">
                    <div className="h-full bg-indigo-500 rounded-full transition-all duration-1000" style={{ width: `${completionRate}%` }}></div>
                  </div>
                </div>
                <div>
                  <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Active</p>
                  <p className="text-2xl font-bold text-white">{stats.active}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Completed</p>
                  <p className="text-2xl font-bold text-emerald-500">{stats.completed}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">High Priority</p>
                  <p className="text-2xl font-bold text-rose-500">{stats.highPriority}</p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="space-y-4">
          {!isAdding ? (
            <div className="flex flex-col md:flex-row gap-4">
              <button 
                onClick={() => setIsAdding(true)}
                className="flex-grow flex items-center gap-4 bg-zinc-900 border border-zinc-800 rounded-2xl py-4 px-4 text-zinc-500 hover:border-zinc-700 hover:bg-zinc-800/50 transition-all text-left"
              >
                <Plus className="w-5 h-5" />
                <span>Add a new task...</span>
              </button>
              
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
                <input 
                  ref={searchRef}
                  type="text"
                  placeholder="Search ( / )"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full md:w-48 bg-zinc-900 border border-zinc-800 rounded-xl py-4 pl-9 pr-4 text-sm text-white focus:outline-none focus:border-zinc-700"
                />
              </div>
            </div>
          ) : (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-zinc-900 border border-zinc-700 rounded-2xl p-6 shadow-2xl"
              ref={formRef}
            >
              <form onSubmit={addTask}>
                <input 
                  autoFocus
                  type="text"
                  placeholder="What needs to be done?"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  className="w-full bg-transparent text-xl font-medium text-white placeholder:text-zinc-600 focus:outline-none mb-6"
                />
                
                <div className="flex flex-wrap gap-4 items-center justify-between">
                  <div className="flex flex-wrap gap-3">
                    <div className="relative group">
                      <select 
                        value={newTaskPriority}
                        onChange={(e) => setNewTaskPriority(e.target.value as Priority)}
                        className="appearance-none bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 pl-8 text-xs font-bold text-zinc-300 focus:outline-none focus:border-indigo-500 cursor-pointer"
                      >
                        {PRIORITIES.map(p => (
                          <option key={p.value} value={p.value}>{p.label} Priority</option>
                        ))}
                      </select>
                      <Flag className={`absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 ${getPriorityColor(newTaskPriority).split(' ')[0]}`} />
                    </div>

                    <div className="relative group">
                      <select 
                        value={newTaskCategory}
                        onChange={(e) => setNewTaskCategory(e.target.value)}
                        className="appearance-none bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 pl-8 text-xs font-bold text-zinc-300 focus:outline-none focus:border-indigo-500 cursor-pointer"
                      >
                        {CATEGORIES.map(c => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                      <Tag className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
                    </div>

                    <div className="relative">
                      <input 
                        type="date"
                        value={newTaskDueDate}
                        onChange={(e) => setNewTaskDueDate(e.target.value)}
                        className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 pl-8 text-xs font-bold text-zinc-300 focus:outline-none focus:border-indigo-500 cursor-pointer"
                      />
                      <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button 
                      type="button"
                      onClick={() => setIsAdding(false)}
                      className="px-4 py-2 rounded-xl text-sm font-bold text-zinc-400 hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                    <button 
                      type="submit"
                      disabled={!newTaskTitle.trim()}
                      className="px-6 py-2 rounded-xl bg-indigo-600 text-white text-sm font-bold hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Add Task
                    </button>
                  </div>
                </div>
              </form>
            </motion.div>
          )}
        </div>
      </header>

      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-900 pb-6">
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
            {(['all', 'active', 'completed'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all whitespace-nowrap ${
                  filter === f 
                    ? 'bg-white text-black' 
                    : 'bg-zinc-900 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300'
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mr-2">Sort:</span>
              <select 
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-transparent text-xs font-bold text-zinc-400 focus:outline-none cursor-pointer hover:text-white transition-colors"
              >
                <option value="newest">Newest</option>
                <option value="priority">Priority</option>
                <option value="dueDate">Due Date</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mr-2">Category:</span>
              <select 
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="bg-transparent text-xs font-bold text-indigo-400 focus:outline-none cursor-pointer"
              >
                <option value="All">All Categories</option>
                {CATEGORIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {filteredTasks.map((task) => (
              <motion.div
                key={task.id}
                layout
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={`group flex items-center gap-4 p-4 rounded-2xl border transition-all ${
                  task.completed 
                    ? 'bg-zinc-950/50 border-zinc-900/50' 
                    : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'
                }`}
              >
                <button 
                  onClick={() => toggleTask(task.id)}
                  className={`flex-shrink-0 transition-all duration-300 ${
                    task.completed ? 'text-indigo-500 scale-110' : 'text-zinc-700 hover:text-zinc-500 hover:scale-110'
                  }`}
                >
                  {task.completed ? <CheckCircle2 className="w-6 h-6" /> : <Circle className="w-6 h-6" />}
                </button>

                <div className="flex-grow min-w-0">
                  {editingTaskId === task.id ? (
                    <input 
                      autoFocus
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onBlur={() => saveEdit(task.id)}
                      onKeyDown={(e) => e.key === 'Enter' && saveEdit(task.id)}
                      className="w-full bg-zinc-800 border border-indigo-500 rounded px-2 py-1 text-white focus:outline-none"
                    />
                  ) : (
                    <h3 
                      onClick={() => startEditing(task)}
                      className={`font-medium truncate transition-all ${
                        task.completed ? 'text-zinc-600 line-through' : 'text-zinc-200 group-hover:text-white cursor-pointer'
                      }`}
                    >
                      {task.title}
                    </h3>
                  )}
                  
                  <div className="flex flex-wrap items-center gap-3 mt-1.5">
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${getPriorityColor(task.priority)}`}>
                      {task.priority}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] font-bold text-zinc-500 uppercase">
                      <Tag className="w-3 h-3" />
                      {task.category}
                    </span>
                    {task.dueDate && (
                      <span className={`flex items-center gap-1 text-[10px] font-bold uppercase ${
                        new Date(task.dueDate) < new Date() && !task.completed ? 'text-rose-500' : 'text-zinc-500'
                      }`}>
                        <Calendar className="w-3 h-3" />
                        {new Date(task.dueDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => startEditing(task)}
                    className="p-2 text-zinc-500 hover:text-indigo-400 transition-colors"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={() => deleteTask(task.id)}
                    className="p-2 text-zinc-500 hover:text-rose-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {filteredTasks.length === 0 && (
            <div className="text-center py-20 bg-zinc-900/20 rounded-3xl border border-dashed border-zinc-800">
              <div className="w-16 h-16 bg-zinc-900/50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-zinc-800" />
              </div>
              <h3 className="text-zinc-400 font-bold uppercase tracking-widest text-sm">No tasks found</h3>
              <p className="text-zinc-600 text-xs mt-2">Try adjusting your filters or add a new task to get started.</p>
            </div>
          )}
        </div>
      </div>

      <footer className="mt-12 pt-8 border-t border-zinc-900 flex justify-between items-center">
        <div className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">
          {filteredTasks.length} {filteredTasks.length === 1 ? 'Task' : 'Tasks'} showing
        </div>
        <div className="flex gap-4">
          <button 
            onClick={() => {
              if(confirm('Clear all tasks?')) setTasks([]);
            }}
            className="text-[10px] font-bold text-zinc-600 hover:text-rose-500 uppercase tracking-widest transition-colors"
          >
            Clear All
          </button>
        </div>
      </footer>
      
      <Chat tasks={tasks} onAddTasks={addSuggestedTasks} />
    </div>
  );
}
