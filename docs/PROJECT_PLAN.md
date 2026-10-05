# Inner Circle: Project Plan

> **Inner Circle** is a private messaging app for you and your closest friends. Chat one-on-one or in group chats, with a built-in AI assistant that catches you up on what you missed, helps plan hangouts, and suggests replies. The assistant only steps in when you ask it to.

This document is the planning spec, written before any code. It covers every page and its features, the tools used to build it, and how hard each feature is given the current skill set (Python, Django, Django REST Framework, SQL, HTML/CSS, Bootstrap, Docker, Git).

---

## Difficulty key

| Label | Meaning |
|---|---|
| ✅ **Known** | Already done in past projects (Django forms, CRUD, auth, REST APIs, SQL) |
| 🟡 **New** | Not done before, but well documented and realistic to learn during this project |
| 🔴 **Stretch** | Harder; build it after everything else works |

---

## 1. Pages and features

### 1.1 Landing page (public)
The first page a logged-out visitor sees.

| Feature | Difficulty |
|---|---|
| App name, tagline, and short description of what Inner Circle does | ✅ |
| Screenshots or GIF of the app in action | ✅ |
| "Sign up" and "Log in" buttons | ✅ |
| "Try the demo" button that logs in as a guest account with sample chats (useful for recruiters) | ✅ |

### 1.2 Sign up (account creation)

| Feature | Difficulty |
|---|---|
| Form fields: username, display name, email, password, confirm password | ✅ |
| Validation: unique username/email, password strength, matching passwords, with clear error messages | ✅ |
| Passwords stored hashed (Django does this by default) | ✅ |
| After sign-up, the user is logged in and sent to a "Set up your profile" step (photo, bio) | ✅ |
| Email verification link before full access | 🟡 |

### 1.3 Log in / log out / forgot password

| Feature | Difficulty |
|---|---|
| Log in with username **or** email plus password | ✅ |
| "Remember me" checkbox (longer session) | ✅ |
| Friendly error on wrong credentials (without revealing which field was wrong) | ✅ |
| Log out button in the navigation bar | ✅ |
| Forgot password: email a reset link, then set a new password (Django has built-in views for this) | 🟡 |
| Rate-limit repeated failed logins | 🟡 |

### 1.4 Home: chat list (inbox)
The main screen after logging in.

| Feature | Difficulty |
|---|---|
| List of all the user's conversations (private and group), newest activity first | ✅ |
| Each row shows: chat name or friend's name, avatar, last message preview, time sent | ✅ |
| Unread message count badge on each chat | 🟡 |
| Online/offline dot next to friends | 🟡 |
| List updates live when a new message arrives (no refresh) | 🟡 |
| Search/filter chats by name | ✅ |
| "New chat" and "New group" buttons | ✅ |

### 1.5 Chat page (private and group messaging)
The core of the app. Private chats and group chats use the same page.

**Messaging**

| Feature | Difficulty |
|---|---|
| Message history with sender name, avatar, and timestamp | ✅ |
| Send a message and see it appear instantly for everyone in the chat (WebSockets) | 🟡 |
| Load older messages when scrolling up (pagination) | 🟡 |
| "Seen" read receipts | 🟡 |
| "Alex is typing…" indicator | 🟡 |
| Edit or delete your own messages (shows "edited" / "message deleted") | ✅ |
| Emoji reactions on messages | 🟡 (v2) |
| Send images | 🟡 (v2) |
| Header shows the friend's name and status, or group name and member count; click it to open the profile or group info | ✅ |

**AI assistant in the chat** (see section 2 for details)

| Feature | Difficulty |
|---|---|
| "Catch me up" button that summarizes unread messages | 🟡 |
| Type `@circle` followed by a question to ask the assistant in the chat | 🟡 |
| Suggested quick replies above the message box | 🟡 |
| "Tone check" before sending a message | 🟡 (v2) |

### 1.6 New chat / create group chat

| Feature | Difficulty |
|---|---|
| **New chat:** pick a friend; opens the existing private chat if one exists, otherwise creates it | ✅ |
| **New group:** name the group, optional group photo, pick friends to add (search with checkboxes) | ✅ |
| The creator becomes the group admin | ✅ |
| Can only add people who are your friends | ✅ |

### 1.7 Group info / settings

| Feature | Difficulty |
|---|---|
| View group name, photo, and member list (who's an admin) | ✅ |
| **Admins:** rename group, change photo, add members, remove members, make another member an admin | ✅ |
| **Everyone:** leave group, mute notifications | ✅ |
| Turn the AI assistant on or off for this group (admin setting) | ✅ |
| System messages appear in the chat, e.g. "Sam added Jordan" | ✅ |
| If the last admin leaves, the oldest member becomes admin automatically | ✅ |

### 1.8 Friends page

| Feature | Difficulty |
|---|---|
| **My friends:** list with avatars and online status, plus Message and View profile buttons | ✅ |
| **Requests:** incoming requests (Accept / Decline) and sent requests (Cancel) | ✅ |
| **Find people:** search users by username or display name, then send a friend request | ✅ |
| Remove a friend | ✅ |
| Block a user: they can't message you, add you, or see your profile | ✅ |
| Live notification badge when a new friend request arrives | 🟡 |

### 1.9 Viewing another user's profile

| Feature | Difficulty |
|---|---|
| Shows profile photo, display name, @username, bio, and date joined | ✅ |
| Mutual friends count and list | ✅ |
| Button that changes with the relationship: **Add friend**, **Request sent**, **Accept request**, or **Message** | ✅ |
| Shared group chats with this person | ✅ |
| Menu: Remove friend / Block / Report | ✅ |
| Privacy: non-friends see a limited profile (name and photo only) | ✅ |

### 1.10 My profile (view and edit)

| Feature | Difficulty |
|---|---|
| See your own profile the way others see it | ✅ |
| Edit display name, bio, and profile photo (with preview) | ✅ |
| Change username (must still be unique) | ✅ |
| Set a status message, e.g. "At work 💼" | ✅ |

### 1.11 Account settings (including delete)

| Feature | Difficulty |
|---|---|
| Change email | ✅ |
| Change password (requires current password) | ✅ |
| **Privacy:** who can send friend requests (everyone or friends of friends) and show/hide online status | ✅ |
| **AI settings:** turn smart replies on or off; opt out of AI summaries that include your messages | ✅ |
| Light/dark theme | ✅ |
| **Delete account:** confirmation screen where you retype your password; your profile and friendships are removed, and your old messages show as "Deleted user" so group chats still make sense | ✅ |
| Download my data (export your messages as a file) | 🔴 (v2) |

### 1.12 Admin panel (for you as site owner)

| Feature | Difficulty |
|---|---|
| Django admin to view users, chats, and reports | ✅ |
| Handle reported users: warn, suspend, or delete | ✅ |

### 1.13 Error pages

| Feature | Difficulty |
|---|---|
| Custom 404 (not found) and 403 (no access, e.g. opening a chat you're not in) pages | ✅ |

---

## 2. AI assistant ("Circle")

The assistant runs on the Claude API. The Django server sends it the relevant messages and returns its answer. It **never reads chats on its own**; it only runs when a user clicks an AI button or types `@circle`.

| Feature | What it does | Where it shows up | Difficulty |
|---|---|---|---|
| **Catch me up** | Summarizes the messages you missed in a busy chat into a few bullet points ("Plans moved to Saturday; Jordan is bringing snacks") | Button at the top of a chat when you have 20+ unread messages | 🟡 |
| **@circle in chats** | Ask a question inside a group chat and the assistant replies as a special "Circle" member. Examples: "@circle what time did we agree on?", "@circle suggest a place to eat near downtown" | Chat page | 🟡 |
| **Smart replies** | Shows 3 short suggested replies based on the last few messages | Above the message box (can be turned off in settings) | 🟡 |
| **Poll maker** | "@circle make a poll: pizza or tacos?" creates a vote in the chat | Chat page | 🔴 (v2) |
| **Tone check** | Before sending, optionally checks if a message might come across as rude and suggests a softer version | Message box | 🟡 (v2) |
| **Search by meaning** | "When did Sam mention the concert?" finds the message even if the exact words differ | Chat search | 🔴 (v2) |

**Is the AI part within your skills? Yes.** Calling the Claude API from Django is a normal Python function call using Anthropic's official `anthropic` library. If you've built REST APIs, you can do this. The new parts to learn are:
1. Writing good prompts (instructions for the AI)
2. Keeping the API key secret (in an environment variable, never in code or GitHub)
3. Running AI requests in the background (Celery) so the chat doesn't freeze while waiting
4. Limiting how often each user can call the AI so costs stay low

**Privacy rules (mention these in the README):**
- The AI only sees messages from the chat it was called in, and only the most recent ones it needs
- Users who opted out are left out of AI summaries
- Group admins can turn the assistant off for their group
- AI replies are clearly labeled as coming from Circle

**Model and cost:** the default choice is Claude Opus 5.5 (`claude-opus-5-5`, $4 per million input tokens and $20 per million output tokens). A "catch me up" summary of about 200 messages costs roughly **2 cents**. Cheaper models (Claude Sonnet 5.5 at $2/$10, Claude Haiku 4.5 at $1/$5) are also an option if you want to cut costs; decide once you can compare the output quality yourself. Set a monthly spending limit in the Anthropic Console so a demo can't run up a bill.

---

## 3. Tools and programs

| Purpose | Tool | Difficulty |
|---|---|---|
| Language | Python 3.12 | ✅ |
| Web framework | Django 5 | ✅ |
| REST API (for AJAX calls and a possible future mobile/React app) | Django REST Framework | ✅ |
| Real-time messaging (WebSockets) | Django Channels and Daphne | 🟡 |
| Message delivery between server processes, plus cache | Redis | 🟡 |
| Background jobs (AI calls, emails) | Celery (with Redis) | 🟡 |
| Database | PostgreSQL (SQLite is fine for quick local tests) | 🟡 (a small change from MySQL) |
| Frontend | Django templates, Bootstrap 5, HTMX, a little JavaScript for the WebSocket | ✅ / 🟡 HTMX |
| AI | Claude API with the `anthropic` Python library | 🟡 |
| Image storage | Local media folder in development; Cloudinary or AWS S3 in production | 🟡 |
| Email (password reset, verification) | Console email backend in development; SendGrid or Mailgun in production | 🟡 |
| Containers | Docker and Docker Compose (web, database, Redis, Celery worker) | ✅ |
| Testing | pytest and pytest-django | 🟡 |
| Code quality | Ruff (linter and formatter) | 🟡 |
| CI (runs tests on each push) | GitHub Actions | 🟡 |
| Hosting | Render, Railway, or Fly.io | 🟡 |
| Version control | Git and GitHub | ✅ |
| Diagrams for the README | draw.io or Excalidraw | ✅ |

---

## 4. Data model (first draft)

| Table | Key fields |
|---|---|
| **User** (extends Django's user) | username, email, display_name, bio, avatar, status_message, last_seen, ai_opt_out |
| **FriendRequest** | from_user, to_user, status (pending/accepted/declined), created_at |
| **Friendship** | user_a, user_b, created_at |
| **Block** | blocker, blocked |
| **Conversation** | type (private/group), name, photo, ai_enabled, created_by, created_at |
| **Membership** | conversation, user, role (member/admin), joined_at, last_read_at, muted |
| **Message** | conversation, sender (null means AI or system), type (text/image/system/ai), body, created_at, edited_at, deleted |
| **Reaction** (v2) | message, user, emoji |
| **Report** | reporter, reported_user, reason, created_at, resolved |

Unread counts come from comparing `Membership.last_read_at` against message timestamps. Private chats and group chats are both `Conversation` rows, so one chat page handles both.

---

## 5. Build order

| Phase | What gets built | Done when… |
|---|---|---|
| **0. Setup** | Django project, Docker Compose, PostgreSQL, Redis, settings via environment variables, GitHub Actions | `docker compose up` runs the app and CI passes |
| **1. Accounts** | Sign up, log in/out, password reset, profile view/edit, account settings, delete account | A user can manage their whole account |
| **2. Friends** | Search users, friend requests, friends list, block, other users' profiles | Two users can become friends |
| **3. Chats (no real-time yet)** | Conversation and message models, inbox, chat page, create group, group settings | Messages work after refreshing the page |
| **4. Real-time** | Channels WebSockets: live messages, typing indicator, read receipts, online status, live inbox | Two browser windows chat instantly |
| **5. AI** | Celery, "catch me up", `@circle`, smart replies, AI settings, rate limits | The demo shows the AI helping in a group chat |
| **6. Polish and launch** | Tests, deployment, guest demo account with sample chats, README with GIF and architecture diagram | A live link is on the resume |
| **7. Version 2 (optional)** | Reactions, images, polls, tone check, search by meaning, data export | — |

---

## 6. Overall feasibility

About **70% of the features are things you've already built** (forms, login, CRUD, permissions, SQL relationships). The new skills are WebSockets (Channels), Redis/Celery, the Claude API, and deployment. Each one is widely used, well documented, and gives you something new to put on your resume. Nothing in phases 0–6 is out of reach. The 🔴 items are left for v2 so they don't block a finished, demo-ready app.
