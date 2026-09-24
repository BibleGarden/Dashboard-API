-- Seed-данные для тестовой БД cep_test
-- Минимальный набор данных для прохождения всех тестов

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- bible_books — все 66 книг (справочник)
-- ============================================================
INSERT INTO bible_books (number, code1, code2, code3, code4, code5, code6, code7, code8, code9, verse_count, short_name_en, short_name_ru, short_name_uk, full_name_en, full_name_ru, full_name_uk) VALUES
(1, 'gen', 'Gen', '01_ge', '01-Genesis', '01_Gen', 'Genesis', '', '002_GEN', '1', 1533, 'Gen', 'Быт', 'Бут', 'Genesis', 'Бытие', 'Буття'),
(2, 'exo', 'Exod', '02_ex', '02-Exodus', '02_Exo', 'Exodus', '', '003_EXO', '2', 1213, 'Ex', 'Исх', 'Вих', 'Exodus', 'Исход', 'Вихід'),
(3, 'lev', 'Lev', '03_le', '03-Leviticus', '03_Lev', 'Leviticus', '', '004_LEV', '3', 859, 'Lev', 'Лев', 'Лев', 'Leviticus', 'Левит', 'Левит'),
(4, 'num', 'Num', '04_nu', '-Numbers', '04_Num', 'Numbers', '', '005_NUM', '4', 1288, 'Num', 'Чис', 'Чис', 'Numbers', 'Числа', 'Числа'),
(5, 'deu', 'Deut', '05_de', '-Deuteronomy', '05_Deu', 'Deuteronomy', '', '006_DEU', '5', 959, 'Deut', 'Втор', 'Втор', 'Deuteronomy', 'Второзаконие', 'Второзаконня'),
(6, 'jos', 'Josh', '06_jos', '06-Joshua', '06_Jos', 'Joshua', '', '007_JOS', '6', 658, 'Josh', 'Нав', 'Нав', 'Joshua', 'Иисус Навин', 'Ісус Навин'),
(7, 'jdg', 'Judg', '07_jud', '07-Judges', '07_Jdg', 'Judges', '', '008_JDG', '7', 618, 'Judg', 'Суд', 'Суд', 'Judges', 'Судьи', 'Суддів'),
(8, 'rut', 'Ruth', '08_ru', '08-Ruth', '08_Rut', 'Ruth', '', '009_RUT', '8', 85, 'Ruth', 'Руфь', 'Рут', 'Ruth', 'Руфь', 'Книга Рут'),
(9, '1sa', '1Sam', '09_1sa', '09-1Samuel', '09_1Sa', '1Samuel', '', '010_1SA', '9', 810, '1Sam', '1Цар', '1Сам', '1 Samuel', '1 Царств', '1 Самуїла'),
(10, '2sa', '2Sam', '10_2sa', '10-2Samuel', '10_2Sa', '2Samuel', '', '011_2SA', '10', 695, '2Sam', '2Цар', '2Сам', '2 Samuel', '2 Царств', '2 Самуїла'),
(11, '1ki', '1Kgs', '11_1ki', '11-1Kings', '11_1Ki', '1Kings', '', '012_1KI', '11', 816, '1Kings', '3Цар', '1Цар', '1 Kings', '3 Царств', '1 Царів'),
(12, '2ki', '2Kgs', '12_2ki', '12-2Kings', '12_2Ki', '2Kings', '', '013_2KI', '12', 719, '2Kings', '4Цар', '2Цар', '2 Kings', '4 Царств', '2 Царів'),
(13, '1ch', '1Chr', '13_1ch', '13-1Chronicles', '13_1Ch', '1Chronicles', '', '014_1CH', '13', 942, '1Chron', '1Пар', '1Хр', '1 Chronicles', '1 Паралипоменон', '1 Хронік'),
(14, '2ch', '2Chr', '14_2ch', '14-2Chronicles', '14_2Ch', '2Chronicles', '', '015_2CH', '14', 822, '2Chron', '2Пар', '2Хр', '2 Chronicles', '2 Паралипоменон', '2 Хронік'),
(15, 'ezr', 'Ezra', '15_ezr', '15-Ezra', '15_Ezr', 'Ezra', '', '016_EZR', '15', 280, 'Ezra', 'Езд', 'Езр', 'Ezra', 'Ездра', 'Ездри'),
(16, 'neh', 'Neh', '16_ne', '-Nehemiah', '16_Neh', 'Nehemiah', '', '017_NEH', '16', 406, 'Neh', 'Неем', 'Неєм', 'Nehemiah', 'Неемия', 'Неємії'),
(17, 'est', 'Esth', '17_es', '17-Esther', '17_Est', 'Esther', '', '018_EST', '17', 167, 'Esther', 'Есф', 'Ест', 'Esther', 'Есфирь', 'Естер'),
(18, 'job', 'Job', '18_job', '-Job', '18_Job', 'Job', '', '019_JOB', '18', 1070, 'Job', 'Иов', 'Іов', 'Job', 'Иов', 'Іова'),
(19, 'psa', 'Ps', '19_ps', '19-Psalms', '19_Psa', 'Psalms', '', '020_PSA', '19', 2461, 'Ps', 'Пс', 'Пс', 'Psalms', 'Псалтирь', 'Псалми'),
(20, 'pro', 'Prov', '20_pr', '20-Proverbs', '20_Pro', 'Proverbs', '', '021_PRO', '20', 915, 'Prov', 'Прит', 'Прип', 'Proverbs', 'Притчи', 'Приповісті'),
(21, 'ecc', 'Eccl', '21_ec', '21-Ecclesiastes', '21_Ecc', 'Ecclesiastes', '', '022_ECC', '21', 222, 'Eccles', 'Еккл', 'Еккл', 'Ecclesiastes', 'Екклесиаст', 'Екклезіаст'),
(22, 'sng', 'Song', '22_so', '-Song of Solomon', '22_Sng', '-Song of Solomon', '', '023_SNG', '22', 117, 'Song', 'Песн', 'Пісн', 'Song of Solomon', 'Песни Песней', 'Пісня над Піснями'),
(23, 'isa', 'Isa', '23_isa', '23-Isaiah', '23_Isa', 'Isaiah', '', '024_ISA', '23', 1292, 'Is', 'Ис', 'Іс', 'Isaiah', 'Исаия', 'Ісаї'),
(24, 'jer', 'Jer', '24_jer', '-Jeremiah', '24_Jer', 'Jeremiah', '', '025_JER', '24', 1364, 'Jer', 'Иер', 'Єр', 'Jeremiah', 'Иеремия', 'Єремії'),
(25, 'lam', 'Lam', '25_la', '-Lamentations', '25_Lam', 'Lamentations', '', '026_LAM', '25', 154, 'Lam', 'Плач', 'Плач', 'Lamentations', 'Плач Иеремии', 'Плач Єремії'),
(26, 'ezk', 'Ezek', '26_eze', '-Ezekiel', '26_Ezk', 'Ezekiel', '', '027_EZK', '26', 1273, 'Ezek', 'Иез', 'Єз', 'Ezekiel', 'Иезекииль', 'Єзекіїла'),
(27, 'dan', 'Dan', '27_da', '-Daniel', '27_Dan', 'Daniel', '', '028_DAN', '27', 357, 'Dan', 'Дан', 'Дан', 'Daniel', 'Даниил', 'Даниїла'),
(28, 'hos', 'Hos', '28_ho', '28-Hosea', '28_Hos', 'Hosea', '', '029_HOS', '28', 197, 'Hos', 'Ос', 'Ос', 'Hosea', 'Осия', 'Осії'),
(29, 'jol', 'Joel', '29_joe', '29-Joel', '29_Jol', 'Joel', '', '030_JOL', '29', 73, 'Joel', 'Иоиль', 'Йоіль', 'Joel', 'Иоиль', 'Йоіла'),
(30, 'amo', 'Amos', '30_am', '30-Amos', '30_Amo', 'Amos', '', '031_AMO', '30', 146, 'Amos', 'Амос', 'Ам', 'Amos', 'Амос', 'Амоса'),
(31, 'oba', 'Obad', '31_ob', '31-Obadiah', '31_Oba', 'Obadiah', '', '032_OBA', '31', 21, 'Obad', 'Авд', 'Авд', 'Obadiah', 'Авдий', 'Авдія'),
(32, 'jon', 'Jonah', '32_jon', '32-Jonah', '32_Jon', 'Jonah', '', '033_JON', '32', 48, 'Jon', 'Иона', 'Йона', 'Jonah', 'Иона', 'Йони'),
(33, 'mic', 'Mic', '33_mic', '33-Micah', '33_Mic', 'Micah', '', '034_MIC', '33', 105, 'Mic', 'Мих', 'Міх', 'Micah', 'Михей', 'Міхея'),
(34, 'nam', 'Nah', '34_na', '34-Nahum', '34_Nam', 'Nahum', '', '035_NAM', '34', 47, 'Nahum', 'Наум', 'Наум', 'Nahum', 'Наум', 'Наума'),
(35, 'hab', 'Hab', '35_hab', '35-Habakkuk', '35_Hab', 'Habakkuk', '', '036_HAB', '35', 56, 'Hab', 'Авв', 'Авак', 'Habakkuk', 'Аввакум', 'Авакума'),
(36, 'zep', 'Zeph', '36_zep', '36-Zephaniah', '36_Zep', 'Zephaniah', '', '037_ZEP', '36', 53, 'Zeph', 'Соф', 'Соф', 'Zephaniah', 'Софония', 'Софонії'),
(37, 'hag', 'Hag', '37_hag', '37-Haggai', '37_Hag', 'Haggai', '', '038_HAG', '37', 38, 'Hag', 'Агг', 'Агг', 'Haggai', 'Аггей', 'Аггея'),
(38, 'zec', 'Zech', '38_zec', '-Zechariah', '38_Zec', 'Zechariah', '', '039_ZEC', '38', 211, 'Zech', 'Зах', 'Зах', 'Zechariah', 'Захария', 'Захарії'),
(39, 'mal', 'Mal', '39_mal', '-Malachi', '39_Mal', 'Malachi', '', '040_MAL', '39', 55, 'Mal', 'Мал', 'Мал', 'Malachi', 'Малахия', 'Малахії'),
(40, 'mat', 'Matt', '40_mt', '40-Matthew', '40_Mat', 'Matthew', '01', '070_MAT', '40', 1071, 'Mt', 'Мф', 'Мт', 'Matthew', 'Евангелие от Матфея', 'Євангелія від Матвія'),
(41, 'mrk', 'Mark', '41_mr', '41-Mark', '41_Mrk', 'Mark', '02', '071_MRK', '41', 678, 'Mk', 'Мк', 'Мк', 'Mark', 'Евангелие от Марка', 'Євангелія від Марка'),
(42, 'luk', 'Luke', '42_lu', '42-Luke', '42_Luk', 'Luke', '03', '072_LUK', '42', 1151, 'Lk', 'Лк', 'Лк', 'Luke', 'Евангелие от Луки', 'Євангелія від Луки'),
(43, 'jhn', 'John', '43_joh', '43-John', '43_Jhn', 'John', '04', '073_JHN', '43', 879, 'Jn', 'Ин', 'Йоан', 'John', 'Евангелие от Иоанна', 'Євангелія від Йоана'),
(44, 'act', 'Acts', '44_ac', '44-Acts', '44_Act', 'Acts', '05', '074_ACT', '44', 1007, 'Acts', 'Деян', 'Діян', 'Acts', 'Деяния апостолов', 'Діяння апостолів'),
(45, 'jas', 'Jas', '59_jas', '59-James', '59_Jas', 'James', '20', '089_JAS', '59', 108, 'Jas', 'Иак', 'Як', 'James', 'Иакова', 'Послання Якова'),
(46, '1pe', '1Pet', '60_1pe', '60-1Peter', '60_1Pe', '1Peter', '21', '090_1PE', '60', 105, '1Pet', '1Пет', '1Пет', '1 Peter', '1 Петра', '1 Петра'),
(47, '2pe', '2Pet', '61_2pe', '61-2Peter', '61_2Pe', '2Peter', '22', '091_2PE', '61', 61, '2Pet', '2Пет', '2Пет', '2 Peter', '2 Петра', '2 Петра'),
(48, '1jn', '1John', '62_1jo', '62-1John', '62_1Jn', '1John', '23', '092_1JN', '62', 105, '1Jn', '1Ин', '1Йоан', '1 John', '1 Иоанна', '1 Йоана'),
(49, '2jn', '2John', '63_2jo', '63-2John', '63_2Jn', '2John', '24', '093_2JN', '63', 13, '2Jn', '2Ин', '2Йоан', '2 John', '2 Иоанна', '2 Йоана'),
(50, '3jn', '3John', '64_3jo', '64-3John', '64_3Jn', '3John', '25', '094_3JN', '64', 15, '3Jn', '3Ин', '3Йоан', '3 John', '3 Иоанна', '3 Йоана'),
(51, 'jud', 'Jude', '65_jude', '65-Jude', '65_Jud', 'Jude', '26', '095_JUD', '65', 25, 'Jude', 'Иуд', 'Юди', 'Jude', 'Иуды', 'Послання Юди'),
(52, 'rom', 'Rom', '45_ro', '45-Romans', '45_Rom', 'Romans', '06', '075_ROM', '45', 433, 'Rom', 'Рим', 'Рим', 'Romans', 'Римлянам', 'Послання до римлян'),
(53, '1co', '1Cor', '46_1co', '46-1Corinthians', '46_1Co', '1Corinthians', '07', '076_1CO', '46', 437, '1Cor', '1Кор', '1Кор', '1 Corinthians', '1 Коринфянам', '1 Коринтян'),
(54, '2co', '2Cor', '47_2co', '47-2Corinthians', '47_2Co', '2Corinthians', '08', '077_2CO', '47', 257, '2Cor', '2Кор', '2Кор', '2 Corinthians', '2 Коринфянам', '2 Коринтян'),
(55, 'gal', 'Gal', '48_ga', '48-Galatians', '48_Gal', 'Galatians', '09', '078_GAL', '48', 149, 'Gal', 'Гал', 'Гал', 'Galatians', 'Галатам', 'Послання до галатів'),
(56, 'eph', 'Eph', '49_eph', '49-Ephesians', '49_Eph', 'Ephesians', '10', '079_EPH', '49', 155, 'Eph', 'Еф', 'Еф', 'Ephesians', 'Ефесянам', 'Послання до ефесян'),
(57, 'php', 'Phil', '50_php', '50-Philippians', '50_Php', 'Philippians', '11', '080_PHP', '50', 104, 'Phil', 'Фил', 'Флп', 'Philippians', 'Филиппийцам', 'Послання до філіппійців'),
(58, 'col', 'Col', '51_col', '51-Colossians', '51_Col', 'Colossians', '12', '081_COL', '51', 95, 'Col', 'Кол', 'Кол', 'Colossians', 'Колоссянам', 'Послання до колосян'),
(59, '1th', '1Thess', '52_1th', '52-1Thessalonians', '52_1Th', '1Thess', '13', '082_1TH', '52', 89, '1Thess', '1Фес', '1Сол', '1 Thessalonians', '1 Фессалоникийцам', '1 Солунян'),
(60, '2th', '2Thess', '53_2th', '53-2Thessalonians', '53_2Th', '2Thess', '14', '083_2TH', '53', 47, '2Thess', '2Фес', '2Сол', '2 Thessalonians', '2 Фессалоникийцам', '2 Солунян'),
(61, '1ti', '1Tim', '54_1ti', '54-1Timothy', '54_1Ti', '1Timothy', '15', '084_1TI', '54', 113, '1Tim', '1Тим', '1Тим', '1 Timothy', '1 Тимофею', '1 Тимофія'),
(62, '2ti', '2Tim', '55_2ti', '55-2Timothy', '55_2Ti', '2Timothy', '16', '085_2TI', '55', 83, '2Tim', '2Тим', '2Тим', '2 Timothy', '2 Тимофею', '2 Тимофія'),
(63, 'tit', 'Titus', '56_tit', '56-Titus', '56_Tts', 'Titus', '17', '086_TIT', '56', 46, 'Tit', 'Тит', 'Тит', 'Titus', 'Титу', 'Послання до Тита'),
(64, 'phm', 'Phlm', '57_phm', '57-Philemon', '57_Phm', 'Philemon', '18', '087_PHM', '57', 25, 'Philem', 'Флм', 'Флм', 'Philemon', 'Филимону', 'Послання до Филимона'),
(65, 'heb', 'Heb', '58_heb', '58-Hebrews', '58_Heb', 'Hebrews', '19', '088_HEB', '58', 303, 'Heb', 'Евр', 'Евр', 'Hebrews', 'Евреям', 'Послання до євреїв'),
(66, 'rev', 'Rev', '66_re', '66-Revelation', '66_Rev', 'Revelation', '27', '096_REV', '66', 404, 'Rev', 'Откр', 'Одкр', 'Revelation', 'Откровение', 'Одкровення Йоана');

-- ============================================================
-- languages
-- ============================================================
INSERT INTO languages (alias, name_en, name_national) VALUES
('ru', 'Russian', 'Русский'),
('en', 'English', 'English'),
('uk', 'Ukrainian', 'Українська');

-- ============================================================
-- translations (code=1 и code=16 используются в тестах)
-- ============================================================
INSERT INTO translations (code, alias, name, description, bibleComDigitCode, removeChapters, language, active) VALUES
(1, 'syn', 'SYNO', 'Синодальный перевод', '400', '["14/37", "19/151"]', 'ru', 1),
(16, 'bsb', 'BSB', 'Berean Standard Bible', '3034', NULL, 'en', 1);

-- ============================================================
-- translation_books
-- ============================================================
INSERT INTO translation_books (code, translation, book_number, name) VALUES
(1, 1, 1, 'Бытие'),
(2, 1, 43, 'От Иоанна святое благовествование'),
(3, 16, 1, 'Genesis'),
(4, 16, 43, 'John');

-- ============================================================
-- translation_verses (после всех миграций: без translation_book)
-- Стихи для тестов: gen 1:1, jhn 3:16-17 (translation=1 и translation=16)
-- ============================================================
INSERT INTO translation_verses (code, translation, book_number, chapter_number, verse_number, verse_number_join, start_paragraph, text, html) VALUES
(1, 1, 1, 1, 1, 0, 1,
 'В начале сотворил Бог небо и землю.',
 'В начале сотворил Бог небо и землю.'),
(2, 1, 43, 3, 16, 0, 0,
 'Ибо так возлюбил Бог мир, что отдал Сына Своего Единородного, дабы всякий верующий в Него, не погиб, но имел жизнь вечную.',
 'Ибо так возлюбил Бог мир, что отдал Сына Своего Единородного, дабы всякий верующий в Него, не погиб, но имел жизнь вечную.'),
(3, 1, 43, 3, 17, 0, 0,
 'Ибо не послал Бог Сына Своего в мир, чтобы судить мир, но чтобы мир спасен был чрез Него.',
 'Ибо не послал Бог Сына Своего в мир, чтобы судить мир, но чтобы мир спасен был чрез Него.'),
(4, 16, 43, 3, 16, 0, 1,
 'For God so loved the world that He gave His one and only Son, that everyone who believes in Him shall not perish but have eternal life.',
 'For God so loved the world that He gave His one and only Son, that everyone who believes in Him shall not perish but have eternal life.'),
(5, 16, 43, 3, 17, 0, 0,
 'For God did not send His Son into the world to condemn the world, but to save the world through Him.',
 'For God did not send His Son into the world to condemn the world, but to save the world through Him.');

-- ============================================================
-- voices (code=1, привязан к translation=1)
-- ============================================================
INSERT INTO voices (code, alias, name, description, translation, is_music, link_template, active) VALUES
(1, 'bondarenko', 'Александр Бондаренко', 'Тестовый голос', 1, 1,
 'https://4bbl.ru/data/syn-bondarenko/{book_zerofill}/{chapter_zerofill}.mp3', 1);

-- ============================================================
-- voice_alignments (таймкоды для seed-стихов)
-- ============================================================
INSERT INTO voice_alignments (code, voice, book_number, chapter_number, verse_number, `begin`, `end`, is_correct) VALUES
(1, 1, 1, 1, 1, 17.650, 24.550, NULL),
(2, 1, 43, 3, 16, 167.570, 179.370, NULL),
(3, 1, 43, 3, 17, 181.090, 188.850, NULL);

-- ============================================================
-- voice_anomalies (2 записи для интеграционных тестов)
-- ============================================================
INSERT INTO voice_anomalies (code, voice, translation, book_number, chapter_number, verse_number, word, position_in_verse, position_from_end, duration, speed, ratio, anomaly_type, status, created_at, updated_at) VALUES
(1, 1, 1, 1, 1, 1, 'в', 1, 7, 0.030, 33.33, 3.88, 'fast', 'detected', NOW(), NULL),
(2, 1, 1, 43, 3, 16, 'так', 3, 15, 0.050, 20.00, 2.50, 'fast', 'detected', NOW(), NULL);

-- ============================================================
-- bible_stat (эталонные данные для проверок)
-- ============================================================
INSERT INTO bible_stat (inc, book_number, chapter_number, verses_count, tolerance_count) VALUES
(1, 1, 1, 31, 0),
(2, 43, 3, 36, 0);

SET FOREIGN_KEY_CHECKS = 1;
