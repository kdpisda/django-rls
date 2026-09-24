---
sidebar_position: 1
---

# Basic Usage

Let's build a simple task management application with RLS to understand the basics.

## The Problem

In a typical Django application, you need to remember to filter querysets:

```python
# Without RLS - Easy to forget filtering!
def task_list(request):
    # WRONG: Shows all tasks to everyone
    tasks = Task.objects.all()

    # RIGHT: Must remember to filter
    tasks = Task.objects.filter(owner=request.user)
    return render(request, 'tasks.html', {'tasks': tasks})
```

## The RLS Solution

With Django RLS, filtering happens automatically at the database level:

### 1. Define Your Model

Use `ModelPolicy` to define rules using standard Django `Q` objects:

```python
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django_rls.models import RLSModel
from django_rls.policies import ModelPolicy, RLS

class Task(RLSModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        rls_policies = [
            # Only allow access to the owner
            ModelPolicy(
                'owner_policy',
                filters=Q(owner=RLS.user_id())
            )
        ]

    def __str__(self):
        return self.title
```

### 2. Create Views

Your views become simpler and more secure:

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Task
from .forms import TaskForm

@login_required
def task_list(request):
    # Automatically filtered to current user's tasks!
    tasks = Task.objects.all()
    return render(request, 'tasks/list.html', {'tasks': tasks})

@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.owner = request.user  # Set owner
            task.save()
            return redirect('task_list')
    else:
        form = TaskForm()
    return render(request, 'tasks/form.html', {'form': form})

@login_required
def task_update(request, pk):
    # Will only find tasks owned by current user
    task = get_object_or_404(Task, pk=pk)
    # ... rest of view
```

### 3. Enable RLS

After creating your models, enable RLS:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py enable_rls
```

## What's Happening Behind the Scenes

When RLS is enabled, `django-rls` translates your `Q` objects into SQL. PostgreSQL then automatically adds WHERE clauses to every query:

```sql
-- What you write:
SELECT * FROM myapp_task;

-- What PostgreSQL executes for user_id=1:
SELECT * FROM myapp_task
WHERE owner_id = current_setting('rls.user_id')::integer;
```

## Complete Example Application

### Models (models.py)

```python
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django_rls.models import RLSModel
from django_rls.policies import ModelPolicy, RLS

class Project(RLSModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        rls_policies = [
            # Owner access
            ModelPolicy('owner_access', filters=Q(owner=RLS.user_id()))
        ]

class Task(RLSModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        rls_policies = [
            # Assigned user access
            ModelPolicy('assigned_access', filters=Q(assigned_to=RLS.user_id()))
        ]
```

### Views (views.py)

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import Project, Task

@login_required
def dashboard(request):
    # All queries automatically filtered!
    context = {
        'projects': Project.objects.all(),
        'tasks': Task.objects.filter(completed=False),
        'completed_tasks': Task.objects.filter(completed=True).count(),
        'project_stats': Project.objects.annotate(
            task_count=Count('task')
        ),
    }
    return render(request, 'dashboard.html', context)
```

## Common Patterns

### Shared Access

Allow multiple users to access the same records:

```python
class SharedDocument(RLSModel):
    title = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    shared_with = models.ManyToManyField(User, related_name='shared_docs')

    class Meta:
        rls_policies = [
            ModelPolicy(
                'access_policy',
                filters=(
                    Q(owner=RLS.user_id()) |
                    Q(shared_with=RLS.user_id()) # Automatic EXISTS subquery!
                )
            )
        ]
```

### Hierarchical Access

Managers can see their team's data:

```python
class TeamTask(RLSModel):
    title = models.CharField(max_length=200)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        rls_policies = [
            ModelPolicy(
                'team_policy',
                filters=(
                    Q(assigned_to=RLS.user_id()) |
                    Q(assigned_to__manager=RLS.user_id()) # Joined field lookup!
                )
            )
        ]
```

### Time-Based Access

Records accessible only during certain periods:

```python
from django.db.models.functions import Now

class TimedContent(RLSModel):
    title = models.CharField(max_length=200)
    available_from = models.DateTimeField()
    available_until = models.DateTimeField()

    class Meta:
        rls_policies = [
            ModelPolicy(
                'time_policy',
                filters=Q(available_from__lte=Now()) & Q(available_until__gte=Now())
            )
        ]
```
