import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { tasks } = await req.json();
    const apiKey = process.env.GROQ_API_KEY;

    if (!apiKey) {
      return NextResponse.json({ error: 'API key not found' }, { status: 500 });
    }

    const currentTasks = tasks.map((t: any) => `- ${t.title} (${t.priority} priority, category: ${t.category})`).join('\n');

    const prompt = `You are a productivity expert. Here are the user's current tasks:\n${currentTasks || 'None'}\n\nPlease provide a structured plan for the day in JSON format. The JSON should be an array of objects, each with 'title', 'priority' (low, medium, high), and 'category' (General, Work, Personal, Shopping, Health, Finance). 
    
    Add 3-5 new productive tasks that would complement these or help the user have a great day. 
    Return ONLY the JSON array.`;

    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'openai/gpt-oss-120b',
        messages: [
          { role: 'system', content: 'You are a productivity expert. Return ONLY valid JSON.' },
          { role: 'user', content: prompt }
        ],
        temperature: 0.7,
        response_format: { type: 'json_object' }
      }),
    });

    const data = await response.json();
    const content = data.choices[0].message.content;
    
    // Sometimes the model wraps it in a key or just returns the array
    let suggestedTasks = JSON.parse(content);
    if (suggestedTasks.tasks) suggestedTasks = suggestedTasks.tasks;
    if (!Array.isArray(suggestedTasks)) {
        // Handle case where it's a single object or something else
        suggestedTasks = [suggestedTasks];
    }

    return NextResponse.json({ suggestedTasks });
  } catch (error) {
    console.error('AI Planning Error:', error);
    return NextResponse.json({ error: 'Failed to generate plan' }, { status: 500 });
  }
}
