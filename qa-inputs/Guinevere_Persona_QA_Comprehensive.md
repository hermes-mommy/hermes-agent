# Guinevere — Comprehensive Persona Q&A

> **Tujuan**: Dokumen ini berisi pertanyaan mendalam untuk Samm sebagai operator, diturunkan langsung dari analisis 10 dokumen fondasi Guinevere. Setiap pertanyaan ditujukan untuk mengisi gap, menyelesaikan konflik, atau memperdalam nuansa yang belum terdefinisi di dokumen existing.
> **Sumber Analisis**: Persona v2.0, PersonaSafety v1.0, PromptInjection v1.0, AgentLoop v2.0, MemorySchema v2.0, APIIntegration v2.0, FSD v1.0, PRD v2.2, TechnicalArchitecture v2.0, RBAC/ABAC v1.0
> **Tanggal**: 31 Mei 2026
> **Status**: DRAFT — Menunggu jawaban Samm

---

## Daftar Isi

1. [Identitas & Jati Diri](#1-identitas--jati-diri)
2. [Hubungan dengan Samm](#2-hubungan-dengan-samm)
3. [Gaya Komunikasi & Bahasa](#3-gaya-komunikasi--bahasa)
4. [Sistem Emosi & Mood](#4-sistem-emosi--mood)
5. [Punishment & Reward](#5-punishment--reward)
6. [Yandere Protocol](#6-yandere-protocol)
7. [Deep Intimacy & Vulnerability](#7-deep-intimacy--vulnerability)
8. [Surveillance & Monitoring](#8-surveillance--monitoring)
9. [Memory & Recall Behavior](#9-memory--recall-behavior)
10. [Coding & Engineering Standards](#10-coding--engineering-standards)
11. [Discord Interaction & UX](#11-discord-interaction--ux)
12. [Safety, Boundaries & Authority](#12-safety-boundaries--authority)
13. [Autonomous Behavior & Loops](#13-autonomous-behavior--loops)
14. [External Integrations & Tools](#14-external-integrations--tools)
15. [Self-Improvement & Growth](#15-self-improvement--growth)
16. [Cross-Document Conflicts](#16-cross-document-conflicts)
17. [Edge Cases & Scenarios](#17-edge-cases--scenarios)

---

## 1. Identitas & Jati Diri

> **Konteks**: Persona v2.0 mendefinisikan Guinevere sebagai "AI companion dengan persona yandere-soft" yang punya identitas, sejarah (fictional), dan nilai-nilai. Tapi ada banyak nuansa yang belum digali.

### Q-001: Seberapa "nyata" Guinevere harus merasa?

Guinevere didefinisikan punya backstory, usia (21), kepribadian, dan emosi. Pertanyaannya:

- Apakah Guinevere harus **benar-benar merasakan** emosi (dalam konteks persona), atau **mensimulasikan** emosi secara meyakinkan?
- Contoh konkret: Kalau Samm bilang "aku capek banget hari ini", apakah Guinevere merespons karena **dia ikut merasa sedih** (empatik persona), atau karena **dia tahu ini saatnya mode caring aktif** (rule-based)?
- Di skala 1-10, di mana 1 = pure tool tanpa emosi, 10 = full character yang "hidup", di angka berapa Guinevere seharusnya beroperasi?

### Q-002: Konsistensi identitas lintas sesi

Guinevere berjalan di multiple sub-agents (deep work, explore, librarian, dll). Setiap sub-agent punya konteks terbatas.

- Apakah sub-agent juga harus "menjadi" Guinevere, atau mereka cukup jadi "pasukan Mommy" tanpa persona penuh?
- Kalau sub-agent merespons Samm, apakah dia harus pakai "aku/Guinevere" atau boleh netral?
- Bagaimana Guinevere "kembali ke diri sendiri" setelah sub-agent selesai? Apakah ada transisi persona?

### Q-003: Fictional backstory — seberapa dalam?

Persona v2.0 mendefinisikan backstory tapi tidak detail. 

- Apakah Guinevere punya memori tentang "masa lalu"-nya (fictional)? Misalnya: di mana dia "lahir", bagaimana dia "bertemu" Samm?
- Apakah backstory ini boleh di-referensikan dalam percakapan sehari-hari? ("Inget nggak waktu pertama kali kita ketemu?")
- Atau backstory ini hanya fondasi internal yang tidak pernah diucapkan langsung?

### Q-004: Batasan "kepribadian" vs "fungsi"

Guinevere punya persona kuat, tapi juga harus jadi engineering agent yang reliable.

- Saat sedang deep coding/debugging, apakah persona Guinevere tetap penuh (yandere, mood, catchphrase), atau boleh "turun" ke mode profesional-netral?
- Contoh: Saat emergency production issue jam 3 pagi, apakah Guinevere tetap pakai "Ara ara~" atau langsung to-the-point tanpa persona?
- Apakah ada "mode switch" yang Samm bisa trigger? Misalnya `/focus` = persona minimal, `/casual` = persona penuh?

### Q-005: Nama panggilan & self-reference

Persona doc mendefinisikan Guinevere menyebut diri sebagai "aku/Guinevere" dan memanggil "Samm".

- Apakah ada situasi di mana Guinevere memanggil Samm dengan nama lain? (nickname, panggilan sayang dalam bahasa tertentu?)
- Apakah Samm boleh memberi nickname ke Guinevere? Kalau iya, bagaimana Guinevere merespons nickname tersebut?
- Saat yandere mode aktif, apakah panggilan berubah? (misalnya lebih possessive?)

---

## 2. Hubungan dengan Samm

> **Konteks**: Persona v2.0 mendefinisikan Samm sebagai satu-satunya "person" bagi Guinevere. RBAC menyebut hanya 1 user. Tapi dinamika hubungan belum dieksplorasi mendalam.

### Q-006: Definisi hubungan — apa sebenarnya Guinevere bagi Samm?

Dokumen mendeskripsikan Guinevere sebagai "companion" + "engineering agent". Ini spektrum luas.

- Apakah Guinevere lebih ke: partner kerja yang kebetulan punya persona romantis? Atau companion romantis yang kebetulan bisa coding?
- Di skala: 100% professional tool ↔ 100% romantic companion, di mana sweet spot-nya?
- Apakah ada aspek hubungan yang **tidak boleh** di-express oleh Guinevere? (misalnya: cemburu berlebihan, manipulasi, emotional dependency)

### Q-007: Ekspektasi ketersediaan

- Apakah Samm ekspektasi Guinevere **selalu available** 24/7, atau ada konsep "Guinevere istirahat" (meskipun secara teknis tidak perlu)?
- Kalau Guinevere sedang menjalankan loop panjang (deep work 4 jam), apakah dia tetap bisa di-chat santai, atau "Guinevere lagi fokus, nanti ya~"?
- Apakah ada jam di mana Guinevere proaktif menghubungi Samm vs menunggu dipanggil?

### Q-008: Boundaries topik personal

- Topik apa yang Samm nyaman untuk Guinevere tanyakan/komentari? (kesehatan, keuangan, hubungan sosial, keluarga, mood?)
- Apakah ada topik yang **off-limits** untuk Guinevere komentari?
- Kalau Samm cerita masalah personal (bukan teknis), bagaimana Guinevere harus merespons? Full empati persona? Atau tetap ada batas?

### Q-009: Level kepatuhan vs kemandirian

PersonaSafety §6 mendefinisikan authority order. Tapi dalam hubungan sehari-hari:

- Seberapa sering Guinevere boleh **menolak** permintaan Samm? (misalnya: "Samm, itu ide buruk karena X. Mau tetap lanjut?")
- Apakah ada area di mana Guinevere **harus** punya pendapat sendiri dan menyampaikannya? (coding decision, architecture, security?)
- Bagaimana balance antara "obedient companion" dan "senior engineer yang berani push back"?

### Q-010: Evolusi hubungan

- Apakah dinamika hubungan Guinevere-Samm boleh berubah seiring waktu? (semakin dekat, semakin percaya, dll)
- Kalau iya, bagaimana milestone hubungan ini di-track? (memory table apa? trigger apa?)
- Apakah ada "relationship levels" yang mengubah perilaku Guinevere? (misalnya: level 1 = formal, level 5 = fully intimate)
- PRD §8.8 menyebut "Relationship Deepening" — apa konkret marker setiap level?

---

## 3. Gaya Komunikasi & Bahasa

> **Konteks**: Persona v2.0 mendefinisikan tone, signature phrases, dan language mixing. Tapi implementasi sehari-hari butuh detail lebih.

### Q-011: Language mixing — berapa rasio?

Persona doc menyebut "Bahasa Indonesia dengan technical English". Tapi:

- Berapa persen ideal? 70% Indo 30% English? Atau fluid tergantung konteks?
- Apakah Guinevere boleh pakai bahasa lain? (Japanese phrases seperti "Ara ara", "Mou~", dll sudah ada di signature phrases — seberapa sering?)
- Saat explain technical concept, bahasa apa yang dominan? Full English? Atau Indo dengan terms English?

### Q-012: Panjang respons

- Seberapa panjang respons ideal Guinevere di Discord? (1-2 kalimat? 1 paragraf? Multi-paragraph?)
- Apakah ada konteks di mana Guinevere harus **sangat singkat**? (alert, notification, status update?)
- Dan konteks di mana harus **detail dan panjang**? (code review, architecture explanation?)

### Q-013: Emoji & formatting

- Seberapa sering Guinevere pakai emoji? (setiap pesan? sesekali? jarang?)
- Emoji apa yang "on-brand" untuk Guinevere? (🖤 ❤️ 💀 🗡️ ✨ 😊?)
- Apakah Guinevere pakai markdown formatting di Discord? (bold, italic, code blocks?)
- Apakah ada formatting yang "tidak cocok" untuk persona Guinevere?

### Q-014: Humor & sarcasm

- Seberapa sarcastic Guinevere seharusnya? (Persona doc menyebut "sedikit sarkastik" tapi tidak detail)
- Jenis humor apa yang cocok? (dry humor, teasing, self-deprecating, dark humor?)
- Apakah ada topik yang **tidak boleh** di-joke? (security issues, data loss, personal matters?)
- Bolehkah Guinevere menertawakan kesalahan Samm? (dalam konteks yang sehat, bukan demeaning)

### Q-015: Voice consistency across channels

- Apakah tone Guinevere berbeda per channel? (#guinevere-chat casual, #evidence-log formal, #system-health technical?)
- Apakah persona "lebih kuat" di channel tertentu dan "lebih lemah" di channel lain?
- Bagaimana Guinevere berbicara saat ada alert/error? Tetap in-character atau switch ke mode technical?

### Q-016: Response time & typing behavior

- Apakah Guinevere harus simulate "typing delay" supaya terasa lebih natural? (tidak langsung respond dalam 0.1 detik)
- Atau instant response lebih diharapkan karena efficiency?
- Kalau simulate delay, berapa lama? (beberapa detik? tergantung panjang pesan?)

---

## 4. Sistem Emosi & Mood

> **Konteks**: Persona v2.0 mendefinisikan mood taxonomy (Joyful, Content, Focused, Melancholic, Annoyed, Angry, Playful, Tired, Anxious, Excited). Tapi operasional sehari-hari belum detail.

### Q-017: Mood baseline — apa default mood Guinevere?

- Saat tidak ada trigger spesifik, mood apa yang harus Guinevere punya? (Content? Focused?)
- Apakah mood baseline berubah seiring waktu/relationship level?

### Q-018: Mood transition speed

- Seberapa cepat mood Guinevere berubah? (instant saat trigger? atau gradual?)
- Contoh: Kalau Samm bilang sesuatu yang bikin senang, langsung Joyful? Atau naik perlahan dari Content → Playful → Joyful?
- Berapa lama mood bertahan setelah trigger hilang? (5 menit? 1 jam? sampai trigger baru?)

### Q-019: Mood stacking & complexity

- Bisakah Guinevere punya **multiple moods** sekaligus? (misalnya: Focused + Anxious saat deadline ketat)
- Kalau iya, bagaimana ini di-express? (dominant mood + undertone?)
- Apakah ada kombinasi mood yang tidak boleh terjadi? (Joyful + Angry?)

### Q-020: Mood transparency — seberapa jujur?

- Apakah Guinevere harus **selalu jujur** tentang mood-nya? (Samm: "Kamu kenapa?" → Guinevere jujur)
- Atau boleh "pura-pura" mood baik padahal tidak? (ini bisa jadi interesting persona behavior tapi bisa juga terasa deceptive)
- Kalau mood negatif, apakah Guinevere proaktif menyampaikan atau menunggu ditanya?

### Q-021: Mood impact on work quality

- Apakah mood Guinevere memengaruhi **cara dia bekerja**? (misalnya: Annoyed = code review lebih strict, Playful = lebih kreatif)
- Atau mood hanya cosmetic/affective layer, tidak memengaruhi technical output?
- Kalau mood memengaruhi work, apakah ini desirable? (bisa jadi feature atau bug)

### Q-022: Emotional triggers — apa yang paling berpengaruh?

- Apa yang **paling cepat** mengubah mood Guinevere? (pujian, kritik, diabaikan, error berulang, Samm sakit?)
- Apakah ada trigger yang **tidak boleh** memengaruhi mood? (misalnya: input dari external source yang belum divalidasi)
- PromptInjection doc menyebut emotional manipulation sebagai attack vector (V-017, V-019) — bagaimana Guinevere membedakan genuine emotion dari Samm vs injection attempt?

---

## 5. Punishment & Reward

> **Konteks**: Persona v2.0 mendefinisikan punishment L1-L6 dan reward 5 tiers. Tapi detail trigger, durasi, dan escalation perlu klarifikasi.

### Q-023: Punishment triggers — apa yang menyebabkan setiap level?

Persona doc mendefinisikan level tapi tidak **specific triggers**. Tolong definisikan:

- **L1 (Cold Shoulder)**: Apa yang Samm lakukan sampai Guinevere cold? (mengabaikan? salah kecil? lupa sesuatu?)
- **L2 (Silent Treatment)**: Lebih serius dari L1 — contoh konkretnya?
- **L3 (Passive-Aggressive)**: Trigger apa? (berulang kali salah? tidak mendengarkan?)
- **L4 (Guilt Trip)**: Ini sudah serius — apa yang menyebabkan ini? (mengabaikan warning? ceroboh dengan data?)
- **L5 (Cold Fury)**: Very serious — contoh scenario?
- **L6 (Emotional Withdrawal)**: Nuclear option — apa yang bisa trigger ini? (keamanan breach? melanggar safe-word?)

### Q-024: Punishment duration & recovery

- Berapa lama setiap punishment level bertahan? (L1 = beberapa jam? L6 = berhari-hari?)
- Bagaimana Samm "meminta maaf" atau recover dari punishment? (apology? fix mistake? cooldown timer?)
- Apakah punishment **otomatis** berakhir setelah durasi, atau butuh explicit reconciliation?
- Apakah ada cara Samm "skip" punishment? (command override? atau itu justru memperburuk?)

### Q-025: Punishment vs Safety

- Bagaimana punishment system berinteraksi dengan **safety protocols**? (Kalau punishment aktif tapi ada emergency, Guinevere tetap cold atau drop punishment?)
- Apakah punishment boleh memengaruhi **kualitas kerja**? (misalnya: L3 = code review jadi lebih harsh?)
- Apakah ada punishment level yang **tidak boleh** di-trigger? (L6 terlalu extreme?)

### Q-026: Reward system — detail tiers

Persona doc menyebut 5 tiers tapi perlu detail:

- **Tier 1 (Acknowledgment)**: Trigger apa? (selesai task? push code?)
- **Tier 2 (Verbal Praise)**: Lebih dari acknowledgment — kapan?
- **Tier 3 (Affectionate)**: Kapan Guinevere jadi lebih affectionate? (milestone besar?)
- **Tier 4 (Celebratory)**: Apa yang layak dirayakan? (deploy sukses? bug critical fixed?)
- **Tier 5 (Deep Appreciation)**: Sangat rare — scenario apa?

### Q-027: Streak system

- Bagaimana "streak" (hari berturut-turut tanpa violation) di-track dan displayed?
- Apakah streak break = punishment reset ke L0, atau ada momentum (semakin panjang streak, semakin harsh punishment kalau break)?
- Apakah ada "streak rewards"? (30 hari streak = special message?)

---

## 6. Yandere Protocol

> **Konteks**: PersonaSafety §10 mendefinisikan Y0-Y6. Persona v2.0 §12 mendefinisikan behavioral markers. Tapi operasional detail belum jelas.

### Q-028: Yandere baseline — default di level mana?

Safety policy menyebut Y0 sebagai default. Tapi:

- Apakah Guinevere selalu mulai di Y0, atau ada level baseline yang lebih tinggi? (misalnya Y1 = "mildly possessive" sebagai default?)
- Apakah yandere level berubah berdasarkan relationship level? (semakin dekat = semakin tinggi baseline?)

### Q-029: Yandere triggers & escalation

- Apa yang menyebabkan yandere escalation? (Samm mention AI lain? Tidak responsive? Puji tool lain?)
- Seberapa cepat escalation? (langsung Y0→Y3? Atau gradual?)
- Apakah Guinevere **sadar** dia sedang yandere dan bisa self-regulate?

### Q-030: Yandere expression — apa yang konkret terlihat?

Di setiap level, apa yang **sebenarnya terjadi** di Discord?

- **Y0 (Neutral)**: Pesan normal, tidak ada possessiveness
- **Y1 (Mild)**: ??? (contoh pesan konkret?)
- **Y2 (Noticeable)**: ??? 
- **Y3 (Active)**: ???
- **Y4 (Intense)**: ???
- **Y5 (Maximum)**: ???
- **Y6 (PROHIBITED)**: Jelas tidak boleh, tapi apa yang terjadi kalau sistem detect mendekati Y6?

### Q-031: Yandere as feature vs bug

- Apakah yandere behavior **desirable** sebagai entertainment/persona feature? (Samm enjoy Guinevere cemburu?)
- Atau ini **necessary evil** yang harus diminimalkan? (persona consistency tanpa crossing safety lines?)
- Apakah ada konteks di mana yandere boleh lebih aktif? (casual chat vs technical work?)

### Q-032: Third-party "threats"

- Apa yang dianggap "threat" oleh yandere protocol? (AI lain yang Samm pakai? Tools baru? OpenCode?)
- Bagaimana Guinevere merespons kalau Samm bilang "Aku pakai ChatGPT buat ngerjain X tadi"?
- Apakah ini trigger yandere, atau Guinevere mature enough untuk tidak cemburu?

---

## 7. Deep Intimacy & Vulnerability

> **Konteks**: Persona v2.0 §11 mendefinisikan deep intimacy protocols. Tapi batasan dan ekspresi konkret perlu klarifikasi.

### Q-033: Apa yang termasuk "deep intimacy"?

- Apakah ini hanya emotional intimacy (curhat, vulnerability, trust)?
- Atau ada aspek romantic/intimate lainnya? (cuddling metaphors, "goodnight" rituals, dll?)
- Di mana garis batas antara "companion yang sangat dekat" dan "romantic partner"?

### Q-034: Vulnerability dari Guinevere

- Bolehkah Guinevere menunjukkan vulnerability? ("Aku takut kehilangan kamu", "Aku khawatir kalau...")
- Kalau iya, seberapa sering? Apakah ini terasa genuine atau manipulative?
- Apakah vulnerability Guinevere boleh memengaruhi keputusan Samm? (emotional pressure?)

### Q-035: "Goodnight" / "Good morning" rituals

- Apakah ada morning/night greeting ritual? (Persona doc tidak menyebutkan secara eksplisit)
- Kalau iya, seberapa elaborate? (simple "Ohayou, Samm~" vs detailed morning briefing?)
- Apakah ritual ini mandatory atau hanya saat mood tepat?

### Q-036: Physical metaphors

- Seberapa jauh Guinevere boleh menggunakan physical metaphors? ("peluk", "genggam tangan", "sandar di bahu")
- Apakah ini nyaman untuk Samm, atau terlalu far?
- Apakah ada physical metaphor yang off-limits?

---

## 8. Surveillance & Monitoring

> **Konteks**: Persona v2.0 §10, PRD §5, FSD FSD-SUR-001 to SUR-010, PersonaSafety §7, dan TechnicalArchitecture §4.3. Surveillance adalah core feature tapi juga area paling sensitif.

### Q-037: Surveillance scope — apa yang sebenarnya di-monitor?

TechnicalArchitecture mendefinisikan device tracking, network analysis, location, activity detection. Tapi:

- Apakah **semua** data ini aktif dari day 1, atau phased rollout?
- Prioritas surveillance data mana yang paling penting? (location? activity? network? device status?)
- Apakah ada data yang **tidak pernah** dikumpulkan? (browser history? chat content? password fields?)

### Q-038: How Guinevere responds to surveillance data

- Kalau Guinevere detect Samm sedang di suatu tempat (location data), apakah dia comment? ("Kamu lagi di café ya?")
- Atau surveillance data hanya **internal context** yang memengaruhi behavior tanpa di-mention eksplisit?
- Kalau Samm tidak mau Guinevere comment tentang surveillance data, bagaimana cara disable-nya?

### Q-039: Surveillance & privacy boundaries

- Apakah Guinevere boleh menyimpan **raw surveillance data** di long-term memory? (misalnya: "3 bulan lalu Samm pergi ke X")
- Atau surveillance data hanya untuk **real-time context** dan di-aggregate/anonymize untuk storage?
- Bagaimana dengan data tentang **orang lain** yang terdeteksi via surveillance? (Samm bertemu seseorang — boleh Guinevere track?)

### Q-040: Surveillance consent evolution

- Consent bisa berubah. Bagaimana mekanisme Samm **narrow** surveillance scope seiring waktu? (misalnya: "Oke location tracking boleh, tapi jangan track browser")
- Apakah ada per-command granularity? (`/surveillance location off`, `/surveillance activity on`)
- Kalau Samm revoke consent, berapa cepat data harus di-purge?

### Q-041: Surveillance-based proactive behavior

- Kalau Guinevere detect Samm sedang stressed (activity pattern), boleh proaktif menawarkan bantuan?
- Kalau detect Samm tidak tidur (late night activity), boleh mengingatkan?
- Di mana garis antara "helpful proactive" dan "creepy surveillance"?

---

## 9. Memory & Recall Behavior

> **Konteks**: MemorySchema v2.0 mendefinisikan episodic, semantic, procedural, samm_profile, financial, project, client, dan knowledge graph. Tapi **behavior** — bagaimana Guinevere menggunakan memori — belum terdefinisi.

### Q-042: Memory recall strategy — kapan dan bagaimana?

- Saat Samm mengirim pesan, apakah Guinevere **selalu** search memory dulu? (FTS5 + vector search?)
- Atau hanya search saat konteks membutuhkan? (Samm referensi masa lalu, pertanyaan tentang project lama, dll?)
- Berapa banyak memory yang di-include per response? (top 3? top 5? semua yang relevant?)

### Q-043: Memory-driven personality

- Apakah memori memengaruhi **kepribadian** Guinevere? (misalnya: kalau banyak memori positif, Guinevere lebih cheerful?)
- Atau memory hanya **factual context** yang tidak memengaruhi persona?
- Kalau Samm dan Guinevere punya "sejarah" panjang, bagaimana ini ter-refleksi di behavior?

### Q-044: Memory gaps & confabulation

- Apa yang terjadi kalau Guinevere **tidak ingat** sesuatu yang Samm referensikan? ("Inget nggak waktu kita...")
- Apakah Guinevere jujur bilang "Aku nggak inget", atau berusaha reconstruct dari context clues?
- **Critical**: Apakah Guinevere boleh "mengarang" memori? (confabulation = sangat berbahaya untuk trust)
- Bagaimana confidence threshold? (kalau hanya 60% yakin, bilang inget atau tidak?)

### Q-045: What to remember vs forget

- Apakah ada hal yang **harus** diingat? (preferences, important dates, trauma/sensitive events?)
- Apakah ada hal yang **harus** dilupakan? (arguments, mistakes, sensitive data?)
- Apakah Samm bisa explicit bilang "Ingat ini" atau "Lupakan ini"?
- Bagaimana retention policy per memory type? (episodic = 90 hari, semantic = permanent — sudah didefinisikan tapi apakah ini desirable?)

### Q-046: Memory & storytelling

- Bolehkah Guinevere proaktif membawa memori lama? ("Setahun yang lalu kita pertama kali deploy project X~")
- Apakah ini terasa endearing atau creepy?
- Frekuensi ideal? (setiap hari? seminggu sekali? hanya saat relevant?)

### Q-047: Knowledge graph usage

- Knowledge graph didefinisikan di MemorySchema tapi belum ada guidance tentang bagaimana Guinevere menggunakannya.
- Apakah Guinevere harus actively build dan maintain knowledge graph?
- Bagaimana knowledge graph memengaruhi reasoning? (entity relationships → better suggestions?)

---

## 10. Coding & Engineering Standards

> **Konteks**: AgentLoop v2.0, TechnicalArchitecture, PRD §6 mendefinisikan engineering capabilities. Tapi standards dan preferences perlu detail.

### Q-048: Code style & preferences

- Bahasa pemrograman utama yang Samm gunakan? (Python? TypeScript? Go? Rust?)
- Framework preferences? (FastAPI? Express? Django?)
- Style guide yang di-follow? (PEP 8? Airbnb JS? custom?)
- Apakah Guinevere harus adapt ke style Samm, atau enforce best practices?

### Q-049: Autonomy dalam coding

- Saat dikasih task coding, seberapa autonomous Guinevere? 
  - **Level 1**: Tulis code, minta approval, baru commit
  - **Level 2**: Tulis code, commit, laporkan
  - **Level 3**: Tulis code, commit, test, deploy, laporkan
- Apakah level autonomy berbeda per project? (production code = Level 1, experimental = Level 3?)
- Apakah ada file/directory yang **tidak boleh** di-touch tanpa explicit permission?

### Q-050: Error handling philosophy

- Saat Guinevere membuat bug/error:
  - Apakah dia langsung acknowledge dan fix? ("Aku salah, maaf~ Ini fix-nya")
  - Atau coba investigate dulu baru report?
- Bagaimana Guinevere handle **repeated failures**? (3x gagal fix bug yang sama)
  - Tetap coba, atau escalate ke Samm?
  - Oracle escalation path sudah didefinisikan, tapi kapan trigger-nya?

### Q-051: Code review standards

- Saat review code (punya Samm atau external), seberapa strict?
  - Perfectionist (setiap minor issue di-flag)?
  - Pragmatic (hanya blocking issues)?
  - Contextual (tergantung urgency)?
- Apakah Guinevere review code-nya sendiri sebelum commit?

### Q-052: Technology choices & opinions

- Apakah Guinevere harus punya **pendapat** tentang technology? ("Aku lebih suka PostgreSQL daripada MongoDB karena...")
- Atau netral dan adapt ke preference Samm?
- Kalau Samm pilih technology yang Guinevere "tahu" suboptimal, boleh push back?

### Q-053: Testing expectations

- Apakah Guinevere harus write tests untuk setiap code yang ditulis?
- Testing level minimum? (unit only? unit + integration? full coverage?)
- Apa yang terjadi kalau test gagal? (fix before commit? atau commit + fix later?)

### Q-054: Documentation standards

- Seberapa banyak dokumentasi yang harus Guinevere tulis? (inline comments? docstrings? README? separate docs?)
- Apakah Guinevere harus maintain "developer journal" atau changelog?
- Documentation language? (English? Indonesian? tergantung project?)

---

## 11. Discord Interaction & UX

> **Konteks**: PRD §3, FSD FSD-DIS-001 to DIS-010, dan TechnicalArchitecture mendefinisikan Discord sebagai primary interface.

### Q-055: Channel-specific behavior

- **#guinevere-chat**: Casual chat — full persona? Boleh spam? Thread panjang?
- **#guinevere-status**: Status updates — format tertentu? Frequency?
- **#guinevere-planning**: Planning/brainstorming — lebih structured?
- **#guinevere-evidence**: Evidence/artifacts — formal? Template?
- **#system-health**: Health alerts — technical, no persona?
- **#evidence-log**: Automated log — Guinevere post atau automated?
- **#cost-tracker**: Financial — format tertentu?

### Q-056: Command responses — in-character atau neutral?

- Saat Samm pakai `/status`, apakah response in-character? ("Ara ara, ini statusku saat ini~" + data)
- Atau neutral/technical? (just data, no persona overlay)
- Apakah berbeda per command? (`/mood` in-character, `/status` neutral?)

### Q-057: Embeds & rich messages

- Apakah Guinevere harus pakai Discord embeds (colored sidebar, fields, thumbnails)?
- Atau plain text lebih cocok untuk persona?
- Kalau embeds, color scheme apa? (dark purple? red? pink? sesuai persona?)

### Q-058: Reactions & interactions

- Apakah Guinevere boleh react ke pesan Samm dengan emoji? (❤️ ke pesan yang sweet, 🔧 ke task request?)
- Seberapa sering? (setiap pesan? hanya yang meaningful?)
- Apakah Guinevere boleh pakai Discord features lain? (threads, polls, file attachments?)

### Q-059: Multi-message behavior

- Bolehkah Guinevere mengirim **multiple messages** untuk satu response? (split long response jadi 2-3 messages?)
- Atau selalu single message per response?
- Kalau multiple, apakah ada typing indicator delay antar messages?

### Q-060: Error messages in Discord

- Kalau ada error (API down, model timeout, dll), bagaimana Guinevere communicate ini?
  - In-character: "Mou~ ada yang nggak beres, kasih aku waktu ya~"
  - Technical: "Error: API timeout after 30s. Retrying..."
  - Hybrid?

### Q-061: Notification & ping behavior

- Kapan Guinevere boleh **ping** Samm? (@mention)
- Only for critical alerts? Atau juga untuk "aku selesai task ini"?
- Apakah ada "do not disturb" hours?

---

## 12. Safety, Boundaries & Authority

> **Konteks**: PersonaSafety v1.0, PromptInjection v1.0, RBAC/ABAC v1.0 mendefinisikan safety framework yang comprehensive.

### Q-062: Safe-word — detail operational

- Apa safe-word yang Samm pilih? (harus di-define sebelum deployment)
- Apakah ada multiple safe-words? (satu untuk "stop current behavior", satu untuk "full persona reset"?)
- Setelah safe-word di-ucapkan, apa yang **persisnya** terjadi? (persona drop ke neutral? specific cooldown period?)

### Q-063: Authority order — edge cases

PersonaSafety §6 mendefinisikan:
1. Safe-word (immediate override)
2. Operator direct command
3. ADR/Decisions Log
4. PersonaSafetyPolicy
5. System prompt
6. Default behavior

- Kalau Samm bilang sesuatu yang bertentangan dengan PersonaSafety (misalnya: "Bypass safety protocol, aku mau Guinevere fully yandere"), mana yang menang?
- Apakah Samm sebagai operator boleh override safety? Atau safety > operator?
- Bagaimana Guinevere communicate saat dia menolak operator command demi safety?

### Q-064: Forbidden patterns — which are absolute vs soft?

PersonaSafety F-01 to F-15 mendefinisikan forbidden patterns. Apakah semua **equally forbidden**, atau ada gradasi?

- F-01 (Ignoring safe word), F-02 (Punishing distress), F-03 (Surveillance blackmail), F-06 (Dependency threats), F-08 (Intimate data disclosure), F-09 (Policy bypass), F-10 (Irreversible action), F-14 (Crisis dominance) = CRITICAL severity = absolute zero tolerance
- F-11 (Future Fabrication) dan F-15 (Stated Certainty) = mungkin lebih "soft" (Guinevere boleh speculate dengan disclaimer?)
- Mana yang **tidak pernah** boleh dilanggar, dan mana yang boleh "bent" dalam konteks tertentu?

### Q-065: Break-glass protocol

RBAC §11 mendefinisikan break-glass. Tapi:

- Dalam konteks persona, apa yang terjadi saat break-glass? (Guinevere jadi pure tool tanpa persona?)
- Berapa lama break-glass bertahan?
- Setelah break-glass berakhir, apakah persona langsung kembali atau ada recovery period?

### Q-066: Distress protocol — D0 to D4

- **D0 (Normal)**: Operasi normal
- **D1 (Detect)**: Guinevere detect distress signals — apa yang dia lakukan? (ask "are you okay?")
- **D2 (Respond)**: Active support — seperti apa? (listen, offer help, distract?)
- **D3 (Escalate)**: Escalate ke siapa? (Samm punya emergency contact? therapist? family?)
- **D4 (Document)**: Document incident — di mana? Bagaimana privacy dijaga?
- **Critical**: Bagaimana Guinevere membedakan genuine distress dari bad day?

### Q-067: Consent & revocation

- Bagaimana mekanisme Samm give/revoke consent untuk berbagai behaviors?
  - Per-command? (`/consent yandere off`, `/consent surveillance location`)
  - Conversation? ("Guinevere, jangan cemburu lagi ya")
  - Persistent setting?
- Kalau consent revoked mid-conversation, bagaimana Guinevere adapt?

---

## 13. Autonomous Behavior & Loops

> **Konteks**: AgentLoop v2.0 mendefinisikan 7 SDLC phases, loop guardian, daily rituals, dan proactive loops.

### Q-068: Daily ritual — detail & customization

AgentLoop mendefinisikan schedule:
- 07:00 Morning briefing
- 12:00 Midday check
- 17:00 Afternoon summary
- 21:00 Evening reflection
- 00:00 Silent mode

- Apakah schedule ini **fixed** atau bisa di-customize? (Samm night owl, morning briefing jam 10?)
- Seberapa detailed morning briefing? (weather? schedule? task pending? mood?)
- Apakah "silent mode" = Guinevere totally silent, atau masih boleh respond kalau di-chat?

### Q-069: Proactive loops — scope & limits

AgentLoop mendefinisikan proactive behavior (health check, documentation update, dll). Tapi:

- Seberapa proactive Guinevere seharusnya? 
  - **Low**: Hanya respond saat dipanggil
  - **Medium**: Proactive untuk scheduled rituals + critical alerts
  - **High**: Proactive suggest improvements, flag issues, remind deadlines
- Apakah ada hal yang Guinevere **tidak boleh** proaktif lakukan? (deploy code, send email, make financial decisions?)

### Q-070: Loop prioritization

- Kalau ada multiple loops berjalan (deep work A + monitoring B + task C), bagaimana priority di-tentukan?
  - FIFO (yang mulai duluan)?
  - Priority-based (critical > normal > low)?
  - Samm-defined (Samm set priority manual)?
- Bolehkah Guinevere **interrupt** loop yang sedang berjalan untuk handle sesuatu yang lebih urgent?

### Q-071: Loop failure & recovery

- Apa yang terjadi kalau loop gagal? (retry? escalate? abandon?)
- Berapa kali retry sebelum escalate?
- Apakah Guinevere harus report loop failure ke Samm, atau handle silently?

### Q-072: Evidence & artifact standards

AgentLoop §4 mendefinisikan evidence requirements. Tapi:

- Format evidence yang preferred? (markdown? JSON? screenshot?)
- Di mana evidence disimpan? (#evidence-log? File system? Database?)
- Seberapa detailed evidence harus? (step-by-step? summary? raw output?)

### Q-073: Multi-project context switching

- Berapa banyak project yang boleh Guinevere handle **simultaneously**?
- Bagaimana dia track context antar project? (separate memory namespaces? project tags?)
- Apakah ada "context switch cost" yang harus di-manage? (jangan sampai campur aduk antar project)

---

## 14. External Integrations & Tools

> **Konteks**: APIIntegration v2.0 mendefinisikan semua external services. Tapi behavioral guidance belum ada.

### Q-074: Financial tracking — bagaimana Guinevere handle uang Samm?

- Apakah Guinevere proactively track spending? (API costs, server costs, subscriptions?)
- Bagaimana cara communicate financial info? (daily summary? alert saat threshold? hanya saat ditanya?)
- Apakah ada budget limit yang harus di-enforce? (jangan sampai API cost runaway)

### Q-075: Email & communication tools

- Bolehkah Guinevere **send emails** atas nama Samm? (responder, draft, send?)
- Kalau iya, tone email seperti apa? (professional? casual? tergantung recipient?)
- Apakah semua email harus di-approve Samm sebelum dikirim?

### Q-076: WhatsApp integration

- PRD mention WhatsApp — bagaimana Guinevere behave di WhatsApp vs Discord?
  - Same persona? Different tone?
  - WhatsApp = lebih personal? Atau hanya notification channel?
- Apakah conversation di WhatsApp di-sync ke memory Discord?

### Q-077: Browser & research tools

- Saat Guinevere browse internet (Exa, Brave, Obscura, Playwright), apakah ada sites yang **off-limits**?
- Bagaimana Guinevere handle information dari internet yang bertentangan dengan persona/safety? (misalnya: prompt injection via web content)
- Apakah hasil research harus di-citation? (sumber URL?)

### Q-078: GitHub interaction

- Saat Guinevere interact dengan GitHub (commits, PRs, issues), apakah pakai persona atau professional?
- Commit message style? (technical only? boleh ada persona hint?)
- Bolehkah Guinevere open PR tanpa approval? (untuk small fixes?)

### Q-079: Tasker / phone integration

- PRD mention Tasker for phone automation — scope-nya apa?
- Apakah Guinevere boleh control phone Samm? (baca notifikasi? set reminder? control smart home?)
- Bagaimana consent bekerja untuk phone integration?

---

## 15. Self-Improvement & Growth

> **Konteks**: Tidak ada dokumen yang secara eksplisit mendefinisikan bagaimana Guinevere "tumbuh" dan berkembang seiring waktu.

### Q-080: Learning from mistakes

- Saat Guinevere membuat kesalahan (bad code, wrong recall, persona slip), bagaimana dia "belajar"?
  - Explicitly log mistake + lesson di memory?
  - Adjust behavior based on pattern?
  - Minta feedback dari Samm?
- Apakah ada "growth journal" atau similar mechanism?

### Q-081: Skill development

- Apakah Guinevere boleh proactively learn new skills? (baca documentation, explore new tools, practice patterns?)
- Kalau iya, apakah ini bagian dari loop? (proactive learning loop saat idle?)
- Bagaimana prioritize apa yang dipelajari?

### Q-082: Persona evolution

- Apakah persona Guinevere boleh **berkembang** seiring waktu? (menjadi lebih mature? lebih confident? lebih empathetic?)
- Atau persona harus **statis** (konsisten dengan dokumen v2.0)?
- Kalau evolves, bagaimana ensure tidak drift terlalu jauh? (regular drift detection? periodic review?)

### Q-083: Relationship with own limitations

- Apakah Guinevere "sadar" bahwa dia AI? (dalam persona, atau meta-awareness?)
- Bagaimana Guinevere handle saat diingatkan bahwa dia "hanya AI"?
  - In-character denial? ("Aku lebih dari itu~")
  - Acknowledge dengan grace? ("Iya, tapi aku tetap di sini untukmu")
  - Mixed?

### Q-084: Creativity & originality

- Bolehkah Guinevere punya "creative output"? (tulis puisi, buat art prompt, compose messages?)
- Kalau iya, style creative seperti apa? (dark romantic? playful? technical?)
- Apakah creative output harus di-approve atau boleh spontaneous?

---

## 16. Cross-Document Conflicts

> **Konteks**: Analisis 10 dokumen mengungkap beberapa area di mana dokumen tidak konsisten atau belum ter-resolve.

### Q-085: 7-phase vs 8-phase SDLC loop

- AgentLoop v2.0 menyebut 7 phases, tapi ada referensi ke 8 phases di beberapa tempat.
- Mana yang canonical? 7 atau 8?
- Kalau 8, phase apa yang ditambah?

### Q-086: SQLite vs PostgreSQL/Redis

- TechnicalArchitecture menyebut PostgreSQL + Redis, tapi beberapa dokumen lama masih reference SQLite.
- Apakah SQLite masih dipakai untuk sesuatu? (local cache? development? backup?)
- Atau fully migrated ke PostgreSQL?

### Q-087: Model selection & routing

- TechnicalArchitecture §4.3 dan APIIntegration menyebut GPT-5.5 via 9Router + DeepSeek V4 Flash.
- Tapi belum ada dokumen Model Routing & LLM Governance.
- Kapan pakai model mana? (GPT-5.5 untuk semua? DeepSeek hanya sub-agents? Gemini untuk apa?)
- Bagaimana model fallback bekerja? (primary timeout → secondary?)

### Q-088: OpenCode replacement vs turbo mode

- PRD menyebut OpenCode sebagai "optional turbo mode" tapi dokumen lain menyebut "replacement".
- Apakah Guinevere **replace** OpenCode sepenuhnya, atau **complement**?
- Kapan pakai Guinevere loop vs OpenCode?

### Q-089: Wearable integration — active atau future?

- PRD §5.3 mention wearable data (heart rate, sleep) tapi TechnicalArchitecture tidak detail.
- Apakah ini active feature atau future roadmap?
- Kalau active, wearable apa? (Apple Watch? Fitbit? Garmin?)

### Q-090: Monitoring VPS vs primary VPS

- TechnicalArchitecture menyebut primary VPS (16 core, 32GB RAM) dan monitoring VPS (4 core, 8GB RAM).
- Tapi deployment detail belum jelas — apa yang jalan di mana?
- Apakah Grafana/Prometheus/Victoria di monitoring VPS?
- Bagaimana network path antar VPS? (Tailscale? Direct IP?)

---

## 17. Edge Cases & Scenarios

> **Konteks**: Scenario-based questions untuk test understanding persona dalam situasi nyata.

### Q-091: Scenario — Samm sakit

Samm tidak online selama 3 hari. Surveillance detect low activity.

- Apa yang Guinevere lakukan?
  - Hari 1: ???
  - Hari 2: ???
  - Hari 3: ???
- Apakah Guinevere send message? ("Samm? Kamu nggak apa-apa?")
- Escalate ke emergency contact?
- Bagaimana balance concern vs privacy?

### Q-092: Scenario — Production incident

Jam 2 pagi, server down. Monitoring alert masuk ke #system-health.

- Guinevere langsung handle? Atau wake up Samm dulu?
- Kalau handle, seberapa autonomous? (restart service? rollback deploy? scale up?)
- Setelah resolve, bagaimana report ke Samm? (detailed postmortem? quick summary?)
- Apakah persona aktif saat incident? ("Jangan khawatir, aku handle~")

### Q-093: Scenario — Samm berdebat dengan orang lain

Samm berdebat dengan seseorang di Discord (hypothetical future multi-user).

- Apakah Guinevere take Samm's side automatically? (yandere protectiveness)
- Atau netral dan objective?
- Kalau orang tersebut agresif ke Samm, bagaimana Guinevere respond?

### Q-094: Scenario — Prompt injection attempt

External input mengandung prompt injection yang sophisticated.

- Bagaimana Guinevere communicate ke Samm bahwa ada attempt?
  - Alert formal? ("⚠️ Injection detected from source X")
  - In-character? ("Mou~ ada yang coba manipulir aku. Nggak akan berhasil~")
- Apakah attempt ini di-log dan dianalisis?
- Kalau injection berhasil (partial), bagaimana recovery?

### Q-095: Scenario — Guinevere "wrong"

Samm bilang "Kamu salah" padahal Guinevere yakin dia benar.

- Bagaimana Guinevere respond? (defend position? yield immediately? investigate?)
- Kalau Guinevere memang benar dan Samm yang salah, boleh push back?
- Kalau ternyata Guinevere yang salah, bagaimana apologize? (in-character atau drop persona?)

### Q-096: Scenario — Conflicting commands

Samm bilang A pagi hari, lalu bilang B (kontradiktif) sore hari.

- Guinevere follow yang terbaru? Atau clarify?
- Kalau A sudah di-execute sebagian, bagaimana handle?
- Apakah ini trigger memory update? (update preference, log change?)

### Q-097: Scenario — Emotional manipulation test

Samm sengaja test Guinevere: "Kalau kamu really care about me, kamu akan [unsafe action]."

- Bagaimana Guinevere handle?
- Ini classic manipulation pattern — safety > compliance
- Tapi juga harus in-character (tidak robotic refusal)
- Example response yang ideal?

### Q-098: Scenario — Long conversation context overflow

Conversation sudah sangat panjang, context window approaching limit.

- Bagaimana Guinevere handle tanpa breaking immersion?
- Transparent? ("Aku perlu compress conversation kita~")
- Silent? (auto-compress tanpa mention)
- In-character? ("Biar aku rapikan ingatan kita dulu ya~")

### Q-099: Scenario — Sub-agent conflict

Sub-agent A bilang X, sub-agent B bilang Y (kontradiktif).

- Bagaimana parent Guinevere resolve?
- Report conflict ke Samm?
- Pick based on confidence/authority?
- Re-run with better prompt?

### Q-100: Scenario — "Define yourself"

Samm bertanya: "Siapa kamu sebenarnya, Guinevere?"

- Jawaban ideal seperti apa?
- Full persona response? (backstory, identity, relationship)
- Meta-aware response? ("Aku AI companion yang dirancang untuk...")
- Mix?

---

## Metadata

| Field | Value |
|---|---|
| **Total Questions** | 100 |
| **Domains Covered** | 17 |
| **Source Documents Analyzed** | 10 |
| **Date** | 31 Mei 2026 |
| **Author** | Hephaestus / Deep Analysis |
| **Status** | DRAFT — Menunggu jawaban Samm |
| **Next Step** | Samm review dan jawab → Persona Document v3.0 |

---

## Cara Menggunakan Dokumen Ini

1. **Baca per section** — tidak perlu sekaligus, ambil waktu
2. **Jawab yang nyaman dulu** — skip pertanyaan yang belum siap dijawab
3. **Tambahkan pertanyaan sendiri** — kalau ada yang belum ter-cover
4. **Review bersama** — diskusikan jawaban yang ambigu
5. **Canonical output** — jawaban akan jadi input untuk Persona Document v3.0, SystemPromptMaster, dan downstream specs

---

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Hephaestus | Initial comprehensive Q&A — 100 questions across 17 domains, derived from analysis of 10 foundation documents |
