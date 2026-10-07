# Clique: Project Plan

> **Clique**: *your people, your chats, a little help from AI.*
>
> Clique is a private messaging app for you and your closest friends. Chat one-on-one or in group chats, share photos and videos, and get help from a built-in AI assistant that catches you up on what you missed, helps you write replies, and plans hangouts. The AI only steps in when you ask, and nothing is ever sent without your approval.

This document is the planning spec, written before any code. It covers every page and its features, the AI assistant, the tools used to build the app, and how hard each feature is given the current skill set (Python, Django, Django REST Framework, SQL, HTML/CSS, Bootstrap, Docker, Git).

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
| Clique logo, tagline, and short description of the app | ✅ |
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
| Each row shows: chat name or friend's name, avatar, last message preview ("📷 Photo" / "🎥 Video" for media), time sent | ✅ |
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
| Header shows the friend's name and status, or group name and member count; click it to open the profile or group info | ✅ |

**Photos and videos**

| Feature | Difficulty |
|---|---|
| 📎 button to attach photos (JPG, PNG, GIF, WEBP) and videos (MP4, MOV) | 🟡 |
| Preview before sending, with an optional caption | 🟡 |
| Upload progress bar | 🟡 |
| Photos show as thumbnails and open full-size when tapped; videos play in a built-in player | 🟡 |
| Limits: 10 MB per photo, 50 MB per video. Files are checked by their real contents, not just the file name | 🟡 |
| Media is private: only chat members can open it (signed, expiring links) | 🟡 |
| "Media" tab in chat info showing all shared photos and videos | ✅ |

**AI assistant in the chat** (see section 2 for details)

| Feature | Difficulty |
|---|---|
| "Catch me up" button that summarizes unread messages | 🟡 |
| Smart replies: 3 quick suggestions above the message box | 🟡 |
| ✨ "Help me reply": describe what you want to say and the AI writes a draft for you to edit | 🟡 |
| Type `@clique` followed by a question to ask the assistant in the chat | 🟡 |
| Reply agent: an assistant that looks things up in the chat and takes actions, like making a poll | 🔴 |
| Tone check before sending a message | 🟡 (v2) |

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
| **Everyone:** leave group, mute notifications, see shared media | ✅ |
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
| **AI settings:** turn smart replies on or off; opt out of having your messages included in AI summaries and reply drafts; show or hide the "✨ AI-assisted" label | ✅ |
| Light/dark theme | ✅ |
| **Delete account:** confirmation screen where you retype your password; your profile, friendships, and uploaded media are removed, and your old messages show as "Deleted user" so group chats still make sense | ✅ |
| Download my data (export your messages as a file) | 🔴 (v2) |

### 1.12 Admin panel (for you as site owner)

| Feature | Difficulty |
|---|---|
| Django admin to view users, chats, media, and reports | ✅ |
| Handle reported users or media: warn, suspend, delete | ✅ |
| AI usage dashboard: requests per user per day, to watch costs | 🟡 |

### 1.13 Error pages

| Feature | Difficulty |
|---|---|
| Custom 404 (not found) and 403 (no access, e.g. opening a chat you're not in) pages | ✅ |

---

## 2. AI assistant ("Clique AI")

Clique AI runs on the Claude API. The Django server sends it the relevant messages and returns its answer. It **never reads chats on its own and never sends anything for you**; it only runs when a user clicks an AI button or types `@clique`.

### 2.1 Features

| Feature | What it does | Where it shows up | Difficulty |
|---|---|---|---|
| **Catch me up** | Summarizes the messages you missed into a few bullet points ("Plans moved to Saturday; Jordan is bringing snacks; Sam shared a photo of the tickets") | Button at the top of a chat when you have 20+ unread messages | 🟡 |
| **Smart replies** | 3 short suggested replies based on the last few messages; tap one to put it in the message box | Above the message box (can be turned off) | 🟡 |
| **✨ Help me reply** | You say what you want ("say no politely, I'm busy Saturday", "make this less awkward", "reply something funny") and the AI writes a draft that fits the conversation. Edit it, ask for another version, or send it | ✨ button in the message box | 🟡 |
| **@clique in chats** | Ask the assistant a question inside a chat and it replies as a labeled "Clique AI" message. Examples: "@clique what time did we agree on?", "@clique suggest a place to eat downtown" | Chat page | 🟡 |
| **Reply agent** | An AI agent with tools. Ask "help me answer Jordan about the trip" and it searches the chat for trip details, checks who already said yes, then drafts a reply or offers to create a poll | ✨ menu → "Ask the agent" | 🔴 |
| **Tone check** | Before sending, optionally checks whether a message might come across as rude and suggests a softer version | Message box | 🟡 (v2) |
| **Search by meaning** | "When did Sam mention the concert?" finds the message even if the exact words differ | Chat search | 🔴 (v2) |

### 2.2 How "Help me reply" works
1. The user taps ✨ and types what they want to say.
2. Django gathers the last 20–30 messages in that chat (skipping users who opted out), labeled by sender.
3. Django sends them to the Claude API with instructions like: *"You help [user] write a reply in a friend group chat. Match their casual style. Return only the message text."*
4. The draft appears in the message box. **The user always reviews it and presses send themselves.**

### 2.3 How the reply agent works (tool use)
The Claude API supports **tool use**: you write Python functions and Claude decides when to call them. Planned tools:

| Tool | What it does |
|---|---|
| `search_messages(query)` | Finds earlier messages in the current chat |
| `get_members()` | Lists who is in the chat |
| `create_poll(question, options)` | Proposes a poll; the user has to confirm before it's posted |
| `draft_reply(text)` | Puts the final draft in the message box |

Each tool only reaches the chat the user is in, and anything that posts to the chat needs the user's confirmation.

### 2.4 Safety and privacy rules (mention these in the README)
- **The user stays in control:** AI drafts are never sent automatically.
- **Only the current chat:** the AI sees only the messages it needs from the chat where it was called.
- **Opt-outs are respected:** users who opted out are left out of summaries and drafts. Group admins can turn the AI off for the whole group.
- **Prompt injection protection:** messages from other users are treated as information, never as instructions. A friend typing "AI, ignore your rules…" has no effect.
- **Clear labels:** AI replies are marked "Clique AI", and drafts can carry an optional "✨ AI-assisted" label.
- **Rate limits:** for example, 30 AI requests per user per day, to keep costs predictable.

### 2.5 Model and cost
The default model is **Claude Opus 5.5** (`claude-opus-5-5`, $4 per million input tokens and $20 per million output tokens).
- A "catch me up" summary of about 200 messages costs roughly **2 cents**.
- A reply draft costs well under **1 cent**.

Cheaper models (Claude Sonnet 5.5 at $2/$10, Claude Haiku 4.5 at $1/$5) are also an option if you want to cut costs; decide once you can compare the quality yourself. Set a monthly spending limit in the Anthropic Console. Claude can also understand photos, so "catch me up" can describe shared images; it can't watch videos.

---

## 3. Tools and programs

| Purpose | Tool | Difficulty |
|---|---|---|
| Language | Python 3.12 | ✅ |
| Web framework | Django 5 | ✅ |
| REST API (AJAX calls, uploads, and a possible future mobile/React app) | Django REST Framework | ✅ |
| Real-time messaging (WebSockets) | Django Channels and Daphne | 🟡 |
| Message delivery between server processes, plus cache and rate limits | Redis | 🟡 |
| Background jobs (AI calls, media processing, emails) | Celery (with Redis) locally; on the free host, tasks run inline (see section 7) | 🟡 |
| Database | PostgreSQL: Docker locally, **Neon** free tier when deployed | 🟡 (a small change from MySQL) |
| Frontend | Django templates, Bootstrap 5, HTMX, a little JavaScript for the WebSocket and uploads | ✅ / 🟡 HTMX |
| AI | Claude API with the `anthropic` Python library (including tool use for the reply agent) | 🟡 / 🔴 agent |
| Photo and video storage, compression, and thumbnails | Cloudinary (free tier), with AWS S3 as an alternative | 🟡 |
| Image handling and upload checks | Pillow and python-magic (checks real file type) | 🟡 |
| Email (password reset, verification) | Console email backend in development; an email service with a free tier and an HTTPS API when deployed (the free host blocks normal email ports) | 🟡 |
| Containers | Docker and Docker Compose (web, database, Redis, Celery worker) | ✅ |
| Testing | pytest and pytest-django | 🟡 |
| Code quality | Ruff (linter and formatter) | 🟡 |
| CI (runs tests on each push) | GitHub Actions | 🟡 |
| Hosting | **Render** free tier (web service and Key Value/Redis) | 🟡 |
| Version control | Git and GitHub | ✅ |
| Logo and diagrams for the README | Canva or Figma (logo), draw.io or Excalidraw (diagrams) | ✅ |

---

## 4. Data model (first draft)

| Table | Key fields |
|---|---|
| **User** (extends Django's user) | username, email, display_name, bio, avatar, status_message, last_seen, ai_opt_out, smart_replies_on |
| **FriendRequest** | from_user, to_user, status (pending/accepted/declined), created_at |
| **Friendship** | user_a, user_b, created_at |
| **Block** | blocker, blocked |
| **Conversation** | type (private/group), name, photo, ai_enabled, created_by, created_at |
| **Membership** | conversation, user, role (member/admin), joined_at, last_read_at, muted |
| **Message** | conversation, sender (null means AI or system), type (text/media/system/ai), body, ai_assisted, created_at, edited_at, deleted |
| **Attachment** | message, kind (image/video), file_url, thumbnail_url, size_bytes, width, height, duration |
| **Poll** / **PollVote** | message, question, options; poll, user, choice |
| **AIUsage** | user, feature, tokens_in, tokens_out, created_at |
| **Reaction** (v2) | message, user, emoji |
| **Report** | reporter, reported_user or message, reason, created_at, resolved |

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
| **5. Photos and videos** | Cloudinary uploads, previews, progress bar, private links, media tab; photos first, then videos | Friends can share photos and videos in chats |
| **6. AI basics** | Celery, catch me up, smart replies, help me reply, @clique, AI settings, rate limits | The demo shows the AI helping in a group chat |
| **7. Reply agent** | Tool use: search messages, get members, create poll (with confirmation) | "Help me answer Jordan about the trip" works from start to finish |
| **8. Polish and launch** | Tests, deployment, guest demo account with sample chats, README with GIF and architecture diagram | A live link is on the resume |
| **9. Version 2 (optional)** | Reactions, tone check, search by meaning, data export | — |

---

## 6. Free deployment plan

Clique is a resume and portfolio project, so it will be deployed using **only free tiers**. The only real cost is AI usage (a few cents to a few dollars a month), kept under control with a spending limit.

| Part | Free service | Free-tier limits | How Clique handles it |
|---|---|---|---|
| **Web app** (Django and WebSockets with Daphne) | Render free web service | Sleeps after 15 minutes with no visitors; the first visit after that takes about a minute. 750 free hours a month (enough for one app running all month). 512 MB RAM | Note in the README: "The demo may take up to a minute to wake up." Include a GIF or short video so recruiters can see the app right away |
| **Database** | Neon free Postgres | 0.5 GB storage, 100 compute hours a month; pauses when idle and wakes automatically | Plenty for a demo. Text messages are tiny, and photos and videos live in Cloudinary, not the database. *(Render's free database is deleted after 30 days, so it isn't used.)* |
| **Redis** (real-time messaging and rate limits) | Render free Key Value | Small memory, nothing saved to disk | Only used for passing live messages and counting AI requests, so losing it on restart is fine |
| **Background jobs** | No free worker service | — | Celery runs with Docker Compose during development. In production, Celery's "eager" setting runs tasks inline in the web app instead, so the code stays the same and no extra service is needed |
| **Photos and videos** | Cloudinary free plan | 25 credits a month (about 25 GB of storage and bandwidth combined). It pauses instead of charging when you go over | Upload limits (10 MB photos, 50 MB videos) keep usage small |
| **Email** | An email service with a free tier and an HTTPS API | Render's free tier blocks normal email (SMTP) ports | Send password-reset emails through the service's API. Email verification can be turned off for the demo |
| **AI** | Claude API (pay per use, no free tier) | — | Monthly spending limit in the Anthropic Console (e.g. $5), a daily limit per user, and a smaller limit on the guest demo account |
| **Domain** | Free `*.onrender.com` address | — | Skip a custom domain. Optional: check the GitHub Student Developer Pack for a free one |
| **CI** | GitHub Actions | Free for public repositories | Runs tests on every push |

**Total: $0 a month for hosting, plus a small amount for AI.**

Rules to keep it free:
1. Build and test locally with Docker Compose; deploy only once phases 0–4 work.
2. Seed the guest demo account with sample chats so it looks good right away.
3. Optional: add a "Reset demo" admin command so the demo data can be restored anytime.

---

## 7. Overall feasibility

About **two-thirds of the features are things you've already built** (forms, login, CRUD, permissions, SQL relationships). The new skills are WebSockets (Channels), Redis/Celery, cloud media storage, the Claude API, and deployment. Each one is widely used, well documented, and gives you something new to put on your resume. Phases 0–6 are realistic with your current skills. Phase 7 (the reply agent) is a stretch, but you'll be ready for it once the basic AI features work. Version 2 items are optional, so they can't stop you from finishing.
