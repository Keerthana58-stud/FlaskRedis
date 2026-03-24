# 🚀 Flask Redis Cache-Aside Application

## 📌 Overview

This project demonstrates a **Cache-Aside Pattern** using **Flask**, **Redis**, and **SQLite**.

The application intelligently serves data either from:

* ⚡ **Redis (cache hit)** for fast responses
* 🗄️ **SQLite database (cache miss)** when data is not cached

It also clearly indicates the **data source** in the response, making it ideal for understanding caching mechanisms.

---

## 🧠 Key Concept: Cache-Aside Pattern

1. Client requests data
2. Application checks Redis:

   * If present → return from cache (**cache hit**)
   * If not → fetch from DB (**cache miss**)
3. Store result in Redis for future use

---

## ⚙️ Tech Stack

* **Backend:** Flask (Python)
* **Cache:** Redis
* **Database:** SQLite
* **Frontend:** HTML, CSS, JavaScript

---

## 📂 Project Structure

```
flask-redis-app/
│── app.py
│── app.db
│── .gitignore
│── static/
│   ├── main.js
│   └── style.css
│── templates/
│   └── index.html
```

---

## 🚀 Features

* 🔁 Cache-aside implementation
* ⚡ Faster responses using Redis
* 🧾 Source tracking (`redis` vs `database`)
* 🔄 Cache refresh support
* 🧹 Cache clear endpoint
* 🌐 Simple frontend UI

---

## 🧪 API Endpoints

### 1. Get User Data

```
GET /user/<id>
```

**Response:**

```json
{
  "id": 1,
  "name": "User1",
  "source": "redis"
}
```

---

### 2. Force Refresh (Bypass Cache)

```
GET /user/<id>?refresh=true
```

---

### 3. Clear Cache

```
GET /clear-cache/<id>
```

---

## 🧰 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Keerthana58-stud/FlaskRedis.git
cd FlaskRedis
```

---

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install flask redis python-dotenv
```

---

### 4. Start Redis

```bash
redis-server
```

---

### 5. Run the application

```bash
python app.py
```

---

## 🧪 Testing Flow

1. Clear cache:

```
/clear-cache/1
```

2. First request:

```
/user/1
```

➡️ Response from **database**

3. Second request:

```
/user/1
```

➡️ Response from **redis**

---

## 📊 Why Redis?

* In-memory storage → ultra-fast reads
* Reduces database load
* Improves scalability
* Ideal for fintech and real-time systems

---

## 🔥 Future Enhancements

* ⏳ Add TTL (auto-expiry for cache)
* 🔐 Authentication & role-based access
* ⚡ Migrate to FastAPI for async performance
* 📈 Monitoring with Prometheus + Grafana
* 🐳 Dockerize the application

---

## 👩‍💻 Author

**Keerthana58-stud**
B.Tech AIML Student | Backend & AI Enthusiast

---

## ⭐ If you found this useful, give it a star!
