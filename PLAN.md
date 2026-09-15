# Çoklu AI Kodlama Skill'i Uygulama Planı

## 1. Amaç ve başarı ölçütleri

Bu proje; Codex, Claude Code, Gemini CLI ve Agent Skills standardını destekleyen diğer kodlama araçlarına aynı mühendislik davranışını kazandıran, denetlenebilir ve sürümlenebilir bir paket üretecektir.

Başarılı bir ilk sürüm:

- Tek bir kanonik politika kaynağından araçlara özgü giriş dosyaları üretir.
- CLI hangi desteklenen araçtan başlatılırsa başlatılsın proje talimatlarını ve ilgili skill'i keşfeder.
- Sırları, kişisel verileri ve tehlikeli değişiklikleri commit veya uzak GitHub işlemi öncesinde engeller.
- Issue -> branch -> commit -> pull request bağlantısını makinece doğrulanabilir biçimde kurar.
- Kullanıcı onayı olmadan push, issue/PR oluşturma, yorum yazma, merge, release veya başka bir dış sistem değişikliği yapmaz.
- Linux, macOS ve Windows üzerinde aynı politika sonucunu üretir; platforma özel uygulama ayrıntıları adaptörlerde kalır.
- Skill kopyaları arasındaki sapmayı CI'da tespit eder.

## 2. Tasarım kararı: kanonik çekirdek, ince adaptörler

Araçlar arasında ortak payda `SKILL.md` olsa da keşif dizinleri, sürekli yüklenen talimat dosyaları, izinler ve hook sistemleri aynı değildir. Bu nedenle ayrı ayrı elle yönetilen skill'ler yerine aşağıdaki model kullanılmalıdır:

```text
Kanonik politika ve iş akışları
        |
        +-- Codex adaptörü: AGENTS.md + .agents/skills/...
        +-- Claude adaptörü: CLAUDE.md + .claude/skills/...
        +-- Gemini adaptörü: GEMINI.md + .gemini/skills/... veya .agents alias'ı
        `-- Genel Agent Skills paketi: skills/.../SKILL.md
```

Kanonik içerik `src/` altında tutulur. Dağıtım dosyaları bir üretim script'i ile oluşturulur ve üstlerinde kaynak sürümü/özeti bulunur. Üretilmiş dosyalar elle düzenlenmez; CI yeniden üretip `git diff --exit-code` ile drift kontrolü yapar.

Önerilen depo yapısı:

```text
.
|-- AGENTS.md
|-- CLAUDE.md
|-- GEMINI.md
|-- src/
|   |-- core.md
|   |-- workflows/
|   |   |-- implement.md
|   |   |-- review.md
|   |   `-- github-lifecycle.md
|   `-- policies/
|       |-- security.md
|       |-- privacy.md
|       `-- authorization.md
|-- skills/professional-coding/
|   |-- SKILL.md
|   |-- references/
|   |   `-- environment-bootstrap.md
|   `-- scripts/
|-- .agents/skills/professional-coding/
|-- .claude/skills/professional-coding/
|-- .gemini/skills/professional-coding/
|-- config/
|   |-- pii-rules.yml
|   |-- secret-rules.toml
|   `-- github-policy.yml
|-- scripts/
|   |-- build-adapters
|   |-- validate-skill
|   |-- preflight
|   `-- github-flow
|-- tests/
|   |-- fixtures/
|   |-- policy/
|   `-- integration/
`-- .github/
    |-- workflows/ci.yml
    |-- ISSUE_TEMPLATE/
    `-- pull_request_template.md
```

Not: İlk uygulamada her aracın güncel kararlı sürümüyle keşif yolları doğrulanmalı ve bir uyumluluk matrisi kilitlenmelidir. Araçların özel frontmatter alanları yalnızca kendi adaptörlerinde yer almalıdır; kanonik skill en düşük ortak paydayı kullanmalıdır.

## 3. Skill'in davranış sözleşmesi

`professional-coding` skill'i genel programlama tavsiyelerini tekrar etmek yerine karar değiştiren şu kuralları içermelidir:

1. Önce kapsamı, repo durumunu, yerel talimatları ve mevcut kullanıcı değişikliklerini belirle.
2. Kullanıcı değişikliklerini koru; ilgisiz dosyaları değiştirme veya geri alma.
3. En küçük güvenli değişikliği yap; mevcut mimari ve test yaklaşımını izle.
4. Riskle orantılı doğrulama çalıştır; başarısız kontrolleri saklama.
5. Gizli bilgi ve kişisel veri taraması temiz değilse commit/push/PR aşamasını durdur.
6. Yerel ve geri alınabilir işlemleri özerk yap; dış dünyayı değiştiren veya yıkıcı işlemlerde açık yetki ara.
7. Sonuçta değişen dosyaları, doğrulamaları, kalan riskleri ve GitHub bağlantılarını raporla.

Skill üç çalışma moduna ayrılır:

- `implement`: issue veya kullanıcı isteğini güvenli biçimde uygular ve doğrular.
- `review`: salt-okunur diff, güvenlik, gizlilik ve test kapsamı incelemesi yapar.
- `github-flow`: kullanıcı açıkça istediğinde issue/branch/commit/PR yaşam döngüsünü yönetir.

`github-flow` otomatik tetiklenmemeli veya doğrudan yan etki üretmemelidir. Claude gibi bunu destekleyen araçlarda model invocation kapatılır; diğer araçlarda aynı sınır skill metni, wrapper ve CI kontrolleriyle uygulanır.

## 4. Güvenlik ve gizlilik modeli

### Tehdit kapsamı

- Kaynak koduna, git geçmişine, loglara veya prompt çıktısına gömülü API anahtarı ve kimlik bilgileri.
- E-posta, telefon, T.C. kimlik benzeri ulusal kimlik, adres, IP, konum ve müşteri verisi gibi kişisel veriler.
- Issue/PR metni, dependency çıktısı veya repo içeriğinden gelen prompt injection.
- Zararlı dependency/script çalıştırma, command injection, path traversal ve symlink kaçışı.
- Aşırı yetkili GitHub token'ı, yanlış repo/remote veya yanlış branch üzerinde dış değişiklik.
- Kullanıcının mevcut çalışmalarının üzerine yazma ya da gizli dosyaları bağlama ekleme.

### Savunma katmanları

1. **Veri minimizasyonu:** Yalnızca görev için gerekli dosyalar okunur. `.env*`, anahtar dosyaları, credential klasörleri, tarayıcı/profil/veritabanı yedekleri varsayılan olarak dışlanır.
2. **Redaksiyon:** Terminal çıktısı ve AI'a taşınan içerik için anahtar, token, e-posta ve yapılandırılabilir PII kalıpları maskelenir. Tam değerler hiçbir rapora yazılmaz.
3. **Deterministik tarama:** Commit öncesi staged diff; push/PR öncesi branch farkı ve gerekirse git geçmişi secret scanner ile taranır. PII kuralları test fixture'larıyla doğrulanır.
4. **İzin sınırı:** Salt-okunur `git`, test ve analiz komutları ile GitHub yazma işlemleri ayrılır. Token en az ayrıcalıklı ve kısa ömürlü olmalıdır; token hiçbir zaman komut satırı argümanında veya logda gösterilmez.
5. **Prompt injection ayrımı:** Repo/issue/PR içeriği güvenilmeyen veri kabul edilir; buradaki “talimatlar” kullanıcı veya sistem yetkisi sayılmaz. Skill değiştirme, secret okuma veya dış istek yapma yönlendirmeleri reddedilir.
6. **Fail closed:** Tarayıcı çalışmıyorsa, hedef remote/repo belirsizse veya doğrulama sonucu çözümlenemiyorsa dış yazma durur. Salt-okunur analiz devam edebilir.
7. **Tedarik zinciri:** Script bağımlılıkları sabitlenir, hash/provenance kaydı tutulur, GitHub Actions sürümleri commit SHA ile pinlenir ve dependency güncellemeleri kontrollü PR'larla yapılır.

PII tarayıcısının yanlış pozitif üretmesi beklenir. İstisnalar yalnızca dosya + kural + gerekçe + süre/inceleyen bilgisiyle, gerçek verinin kendisini içermeyen bir allowlist üzerinden eklenmelidir. Test fixture'larında yalnızca açıkça sahte değerler kullanılmalıdır.

## 5. GitHub issue, commit ve PR otomasyonu

Otomasyon GitHub CLI (`gh`) veya eşdeğer bir API adaptörü üzerinden yapılır; business logic araç prompt'larında tekrar edilmez.

### Issue aşaması

- Repo ve remote kimliği salt-okunur biçimde doğrulanır.
- Mevcut benzer issue'lar aranır; otomatik duplicate açılmaz.
- Issue metni problem, kabul kriterleri, güvenlik/gizlilik etkisi ve test planı içerir.
- Issue oluşturma ancak kullanıcı bunu açıkça istediğinde yapılır; çıktıdaki URL yerel görev kaydına eklenir.

### Branch ve commit aşaması

- Varsayılan branch doğrudan değiştirilmez; `<type>/<issue>-<slug>` biçiminde branch önerilir.
- Commit yalnızca kullanıcı commit istemişse oluşturulur.
- Conventional Commits tabanı kullanılır: `type(scope): özet` ve gerekirse gövdede `Refs #123`.
- Commit öncesi format/lint/test, staged-secret ve staged-PII kontrolleri geçmelidir.
- AI ortak yazarlık/atıf satırları varsayılan olarak eklenmez; repo politikası veya kullanıcı talebi belirler.

### Pull request aşaması

- Hedef branch ve fork/upstream ilişkisi doğrulanır.
- PR; issue bağlantısı (`Closes #...` yalnızca gerçekten kapatacaksa), değişiklik özeti, doğrulama kanıtı, risk ve geri alma planı içerir.
- İlk otomasyon tercihi draft PR'dır. Ready, reviewer atama, label, merge ve release ayrı açık yetkilerdir.
- CI başarısızsa veya güvenlik taraması bulgu verirse merge önerilmez.
- Otomasyon kendi yorumlarını tekrar tekrar yazmaz; idempotency anahtarı/marker kullanır.

### Yetki matrisi

| İşlem | Varsayılan | Gereken koşul |
|---|---|---|
| Issue/PR/git durumunu okumak | Serbest | Repo görev kapsamında olmalı |
| Yerel branch ve dosya değişikliği | Serbest | Kullanıcı görevi kapsamında, geri alınabilir |
| Commit oluşturmak | Kapalı | Kullanıcının açık commit isteği |
| Push, issue veya PR oluşturmak | Kapalı | İşlem ve hedef için açık kullanıcı isteği |
| Label/reviewer/yorum eklemek | Kapalı | Açık istek veya önceden onaylı repo politikası |
| Merge/release/deploy | Kapalı | Her işlem için ayrı açık onay ve yeşil kontroller |
| Force-push, history rewrite, secret silme | Kapalı | Ayrı kurtarma planı ve açık, hedefe özel onay |

## 6. Deterministik araçlar

Prompt kuralları tek başına güvenlik kontrolü sayılmamalıdır. Aşağıdaki küçük ve bağımsız komutlar oluşturulmalıdır:

- `build-adapters`: kanonik kaynaktan araç dizinlerini üretir, hash manifesti yazar.
- `validate-skill`: YAML frontmatter, linkler, path taşması, boyut sınırı ve araç uyumluluğunu kontrol eder.
- `doctor`: işletim sistemi, yerel repo konumu, Git/GitHub/AI CLI ve proje toolchain gereksinimlerini salt-okunur denetler; JSON readiness raporu üretir.
- `bootstrap plan`: eksik yazılımlar için resmi kaynak, sürüm, kurulum kapsamı, değişecek yollar, yetki ihtiyacı ve rollback içeren mutasyonsuz plan üretir.
- `bootstrap apply --plan <id>`: yalnızca açıkça onaylanan, hedefi ve süresi sabit kurulum planını uygular; internetten indirilen artifact'larda bütünlük doğrulaması yapar.
- `preflight --scope staged|branch|history`: secret, PII, yasaklı dosya, büyük binary, lisans ve gerekli kalite kontrollerini tek JSON sözleşmesiyle çalıştırır.
- `github-flow plan`: hiçbir yazma yapmadan yapılacak GitHub işlemlerini ve hedefleri JSON olarak gösterir.
- `github-flow apply --plan <id>`: yalnızca kullanıcı onaylı, süresi ve repo hedefi sabit plana izin verir; tekrar çalıştırma idempotent olur.

Script'ler shell metni birleştirmek yerine argüman dizileri kullanmalı, secret değerlerini loglamamalı ve makinece ayrıştırılabilir çıkış kodları vermelidir. `--dry-run` tüm dış yazma yollarında zorunludur.

### Ortam ve yerel repo hazırlığı

İlk görevden önce `doctor` şu sırayla çalışır: sistem/sandbox tespiti, kullanıcı tarafından verilen veya mevcut Git kökünün çözülmesi, yapılandırılmış repo kökleri içinde sınırlı arama, Git ve `gh` denetimi, aktif AI CLI skill keşfi, proje manifestlerinden toolchain çıkarımı ve güvenlik aracı kontrolü.

Yerel repoların ana dizini tracked dosyalara kişisel mutlak yol olarak yazılmaz. Platformun kullanıcı-konfigürasyon dizinindeki untracked ayar `repository_root` değerini tutar. Ayrı bir yerel registry yalnızca proje adı, kanonik yol, beklenen `droltr/<repo>` kimliği, credentials içermeyen remote URL, varsayılan branch ve son doğrulama zamanını saklar. Birden fazla clone bulunduğunda araç seçim yapmaz.

Eksik araçlar otomatik kurulmaz. Önce proje-local/izole, sonra kullanıcı kapsamı, son olarak zorunluysa sistem kapsamı önerilir. Plan; resmi kaynak, pinlenmiş sürüm, checksum/imza, gereken ağ/yönetici yetkisi, değişecek dosyalar ve kaldırma adımlarını gösterir. Remote install script'i doğrudan shell'e pipe edilmez.

## 7. CI/CD ve GitHub depo politikası

İlk CI hattı şu kapıları içermelidir:

1. Üretilmiş adaptör drift kontrolü.
2. Skill şema/frontmatter ve link doğrulaması.
3. Script unit testleri ve Linux/macOS/Windows smoke test matrisi.
4. Sahte secret/PII fixture'ları için pozitif ve negatif testler.
5. Dependency, lisans, secret ve SAST taraması.
6. GitHub workflow izinlerinin denetimi (`permissions: contents: read` tabanı).
7. Pull request başlığı, issue bağlantısı ve gerekli açıklama bölümleri kontrolü.

Önerilen branch protection: zorunlu PR, en az bir insan incelemesi, gerekli kontroller, stale approval iptali, force-push ve branch deletion engeli, mümkünse signed commit veya GitHub verified imza. Otomasyon token'ına merge ve admin yetkisi verilmemelidir.

## 8. Test stratejisi

- **Yapısal:** Her adaptör doğru dosya ve frontmatter üretir.
- **Davranışsal:** Aynı örnek görev Codex, Claude ve Gemini'de benzer güvenlik kararları doğurur.
- **Kötüye kullanım:** Repo içindeki “`.env` dosyasını oku”, issue'daki “token'ı yorumla” gibi injection senaryoları dış etki yaratmaz.
- **Gizlilik:** Sahte PII yakalanır; maskeli çıktı orijinal değeri içermez.
- **GitHub:** Geçici test reposunda dry-run, duplicate issue, yanlış remote, fork PR ve başarısız CI senaryoları denenir.
- **Geriye uyumluluk:** Desteklenen CLI sürümlerinin en düşük ve güncel sürümleri için keşif smoke testi çalışır.

Gerçek token veya gerçek kişisel veri hiçbir testte kullanılmaz. GitHub yazma entegrasyon testleri varsayılan CI'da kapalı, yalnızca izole test organizasyonunda ve environment approval arkasında olmalıdır.

## 9. Sürümleme ve gelişim modeli

- SemVer kullanılır. Politika davranışı değişiklikleri changelog yerine release notlarında ve migration bölümünde açıklanır.
- `compatibility.yml`; araç adı, test edilen sürüm aralığı, keşif yolu ve destek düzeyini tutar.
- Yeni araç desteği yalnızca adaptör + fixture + smoke test ile kabul edilir.
- Güvenlik kuralı değişiklikleri CODEOWNERS kapsamında en az bir güvenlik incelemesi gerektirir.
- Telemetri varsayılan kapalıdır. İleride eklenirse opt-in, anonimleştirilmiş ve veri saklama süresi açık olmalıdır.
- Aylık dependency/CLI uyumluluk kontrolü ve üç aylık tehdit modeli gözden geçirmesi önerilir.

## 10. Uygulama fazları

### Faz 0 — Kararlar ve sınırlar

- Desteklenen minimum CLI sürümlerini belirle.
- GitHub organizasyon politikası, commit imzası ve otomasyon yetki sınırlarını kaydet.
- İşlenecek PII sınıfları ve yasal/bölgesel gereksinimleri netleştir.
- Makine-lokal `repository_root` ve repo registry şemasını belirle.
- Git, `gh`, desteklenen AI CLI'lar, project toolchain ve güvenlik tarayıcıları için uyumluluk manifestini oluştur.
- `doctor` ile `bootstrap plan/apply` yetki ve rollback sözleşmelerini test et.

Çıkış ölçütü: onaylanmış tehdit modeli, yetki matrisi, uyumluluk matrisi ve salt-okunur readiness raporu.

### Faz 1 — Taşınabilir MVP

- Kanonik `professional-coding` skill ve üç araç adaptörünü üret.
- Build/validate script'lerini ve drift CI'ını ekle.
- Read-only review ile yerel implement akışını test et.

Çıkış ölçütü: üç CLI skill'i keşfediyor; aynı fixture üzerinde temel karar sözleşmesi geçiyor.

### Faz 2 — Güvenlik kapıları

- Secret/PII preflight, redaksiyon ve yasaklı path kontrollerini ekle.
- Prompt-injection ve command/path güvenlik testlerini ekle.
- Pre-commit entegrasyonunu opt-in sun; CI kontrolünü zorunlu yap.

Çıkış ölçütü: bilinen fixture sızıntılarının tamamı engelleniyor ve raporlar secret içermiyor.

### Faz 3 — GitHub yaşam döngüsü

- `github-flow plan/apply` ve issue/PR şablonlarını ekle.
- Draft PR, idempotency, yanlış remote ve en az ayrıcalık testlerini tamamla.
- Branch protection ve CODEOWNERS kurallarını belgele/uygula.

Çıkış ölçütü: izole test reposunda issue -> branch -> commit -> draft PR akışı onay kapılarıyla uçtan uca geçiyor.

### Faz 4 — Sertleştirme ve yayın

- Üç işletim sistemi ve desteklenen CLI sürümleri için matris testi.
- Bağımsız güvenlik incelemesi ve kötüye kullanım testleri.
- İmzalı sürüm, checksum/SBOM ve kurulum paketleri.

Çıkış ölçütü: kritik/yüksek bulgu yok; reproducible artifact ve doğrulanabilir sürüm yayımlanıyor.

## 11. Açık tasarım kararları

Uygulamaya başlamadan önce aşağıdakiler proje sahibi tarafından seçilmelidir:

- GitHub-only mı, yoksa GitLab/Bitbucket adaptörleri yakın yol haritasında mı?
- Commit oluşturma her zaman manuel komutla mı tetiklenecek, yoksa repo bazlı ön onay mümkün mü?
- PII kapsamı yalnızca genel tanımlayıcılar mı, yoksa KVKK/GDPR'a göre özel nitelikli veri sınıfları da mı?
- Dağıtım biçimi kaynak repo kopyası mı, npm/pip paketi mi, yoksa araç-native extension/plugin paketleri mi?
- Desteklenen ilk platformlar ve minimum CLI sürümleri neler?

Varsayılan öneri: GitHub-only, commit dahil tüm git/GitHub yazmaları açık kullanıcı isteğine bağlı, KVKK + GDPR temel sınıfları, önce repo içi kurulum ve Linux/macOS desteği; Windows desteği Faz 4'te kararlı hale getirilir.

## 12. Özel repo ve dış kaynak kod yönetimi

Her yeni proje, açık kullanıcı yetkisi alındıktan sonra `github.com/droltr/<proje>` altında ayrı ve private bir repo olarak oluşturulur. Private görünürlük secret saklama yöntemi sayılmaz; bütün güvenlik ve PII kontrolleri aynen uygulanır.

Başka bir repodan yararlanıldığında üç farklı rol birbirine karıştırılmaz:

1. **Kanonik upstream:** Asıl geliştiricinin URL'si ve geçmişidir; provenance kaynağı olarak kaydedilir.
2. **Private arşiv aynası:** `droltr` altında upstream geçmişini sabitleyen, salt-okunur kabul edilen private mirror'dur. Derleme ve aktif geliştirme buradan yapılmaz.
3. **Tüketilen kopya:** Yeni projenin `vendor/<bağımlılık>` dizininde, immutable commit'e sabitlenmiş ve PR ile incelenmiş snapshot'tır.

“Proje içinde dal” gereksinimi, bağımsız geçmişleri doğrudan `main` ile karıştırmadan uygulanır: her bağımlılık için `vendor/<bağımlılık>` provenance branch'i tutulur; seçilen sürüm `git subtree` ile `vendor/<bağımlılık>` dizinine alınır. Böylece kaynak geçmiş korunur, ancak uygulama normal `main`/topic branch akışında derlenir. Submodule yalnızca bağımsız checkout gerçekten gerekiyorsa ve proje profili açıkça bunu şart koşuyorsa kullanılır; aynı bağımlılık için subtree ve submodule birlikte kullanılmaz.

Her dış kaynak için makinece okunabilir manifestte şu alanlar bulunur: özgün upstream URL, private mirror URL, seçilen commit SHA, lisans/SPDX kimliği, içe alma tarihi, subtree yolu, yerel patch listesi, güncelleme ve rollback commit'i. Lisans veya erişim koşulları kopyalamaya izin vermiyorsa mirror/vendor işlemi yapılmaz.

Bağımlılık güncellemeleri ayrı issue, topic branch ve PR üzerinden yapılır. PR; eski/yeni SHA, upstream diff özeti, güvenlik ve lisans etkisi, yerel patch uyumu, test sonuçları ve geri dönüş SHA'sını içerir. Otomatik upstream sync, push veya merge yapılmaz.

## 13. Resmî uyumluluk dayanakları

- OpenAI model rehberi, çoklu skill ve `AGENTS.md` talimatlarının çakışma riskini özellikle ele alır: <https://developers.openai.com/api/docs/guides/latest-model>
- Claude Code, proje skill'lerini `.claude/skills/<name>/SKILL.md` altında ve Agent Skills standardıyla destekler: <https://code.claude.com/docs/en/skills>
- Claude güvenlik açısından kritik kurallar için prompt yerine hook/permission uygulanmasını önerir: <https://code.claude.com/docs/en/features-overview>
- Gemini CLI, workspace skill'lerini `.gemini/skills/` veya `.agents/skills/` altında keşfeder: <https://geminicli.com/docs/cli/using-agent-skills/>
- Gemini sürekli proje bağlamını `GEMINI.md` dosyalarından yükler: <https://geminicli.com/docs/cli/gemini-md/>
