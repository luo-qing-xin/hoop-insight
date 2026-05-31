export type NameTranslationMode = "full" | "short" | "original";

type NameTranslation = {
  full: string;
  short: string;
  aliases?: string[];
};

export const TEAM_NAME_TRANSLATIONS: Record<string, NameTranslation> = {
  "Los Angeles Lakers": { full: "洛杉矶湖人", short: "湖人", aliases: ["Lakers", "LA Lakers", "LAL"] },
  "Golden State Warriors": { full: "金州勇士", short: "勇士", aliases: ["Warriors", "GSW", "GS"] },
  "Boston Celtics": { full: "波士顿凯尔特人", short: "凯尔特人", aliases: ["Celtics", "BOS"] },
  "Denver Nuggets": { full: "丹佛掘金", short: "掘金", aliases: ["Nuggets", "DEN"] },
  "Milwaukee Bucks": { full: "密尔沃基雄鹿", short: "雄鹿", aliases: ["Bucks", "MIL"] },
  "Phoenix Suns": { full: "菲尼克斯太阳", short: "太阳", aliases: ["Suns", "PHX", "PHO"] },
  "Dallas Mavericks": { full: "达拉斯独行侠", short: "独行侠", aliases: ["Mavericks", "Mavs", "DAL"] },
  "Miami Heat": { full: "迈阿密热火", short: "热火", aliases: ["Heat", "MIA"] },
  "New York Knicks": { full: "纽约尼克斯", short: "尼克斯", aliases: ["Knicks", "NYK"] },
  "Brooklyn Nets": { full: "布鲁克林篮网", short: "篮网", aliases: ["Nets", "BKN", "BRK"] },
  "Philadelphia 76ers": { full: "费城 76 人", short: "76 人", aliases: ["76ers", "Sixers", "PHI"] },
  "Cleveland Cavaliers": { full: "克利夫兰骑士", short: "骑士", aliases: ["Cavaliers", "Cavs", "CLE"] },
  "Chicago Bulls": { full: "芝加哥公牛", short: "公牛", aliases: ["Bulls", "CHI"] },
  "Los Angeles Clippers": { full: "洛杉矶快船", short: "快船", aliases: ["Clippers", "LA Clippers", "LAC"] },
  "Memphis Grizzlies": { full: "孟菲斯灰熊", short: "灰熊", aliases: ["Grizzlies", "MEM"] },
  "Minnesota Timberwolves": { full: "明尼苏达森林狼", short: "森林狼", aliases: ["Timberwolves", "Wolves", "MIN"] },
  "Oklahoma City Thunder": { full: "俄克拉荷马城雷霆", short: "雷霆", aliases: ["Thunder", "OKC"] },
  "Sacramento Kings": { full: "萨克拉门托国王", short: "国王", aliases: ["Kings", "SAC"] },
  "San Antonio Spurs": { full: "圣安东尼奥马刺", short: "马刺", aliases: ["Spurs", "SAS", "SA"] },
  "Houston Rockets": { full: "休斯顿火箭", short: "火箭", aliases: ["Rockets", "HOU"] },
  "New Orleans Pelicans": { full: "新奥尔良鹈鹕", short: "鹈鹕", aliases: ["Pelicans", "NOP", "NO"] },
  "Portland Trail Blazers": { full: "波特兰开拓者", short: "开拓者", aliases: ["Trail Blazers", "Blazers", "POR"] },
  "Utah Jazz": { full: "犹他爵士", short: "爵士", aliases: ["Jazz", "UTA"] },
  "Atlanta Hawks": { full: "亚特兰大老鹰", short: "老鹰", aliases: ["Hawks", "ATL"] },
  "Charlotte Hornets": { full: "夏洛特黄蜂", short: "黄蜂", aliases: ["Hornets", "CHA", "CHO"] },
  "Detroit Pistons": { full: "底特律活塞", short: "活塞", aliases: ["Pistons", "DET"] },
  "Indiana Pacers": { full: "印第安纳步行者", short: "步行者", aliases: ["Pacers", "IND"] },
  "Orlando Magic": { full: "奥兰多魔术", short: "魔术", aliases: ["Magic", "ORL"] },
  "Toronto Raptors": { full: "多伦多猛龙", short: "猛龙", aliases: ["Raptors", "TOR"] },
  "Washington Wizards": { full: "华盛顿奇才", short: "奇才", aliases: ["Wizards", "WAS", "WSH"] },
};

export const PLAYER_NAME_TRANSLATIONS: Record<string, NameTranslation> = {
  "LeBron James": { full: "勒布朗·詹姆斯", short: "詹姆斯", aliases: ["Lebron James"] },
  "Stephen Curry": { full: "斯蒂芬·库里", short: "库里", aliases: ["Steph Curry"] },
  "Kevin Durant": { full: "凯文·杜兰特", short: "杜兰特", aliases: ["KD"] },
  "Nikola Jokic": { full: "尼古拉·约基奇", short: "约基奇", aliases: ["Nikola Jokić"] },
  "Luka Doncic": { full: "卢卡·东契奇", short: "东契奇", aliases: ["Luka Dončić"] },
  "Giannis Antetokounmpo": { full: "扬尼斯·阿德托昆博", short: "字母哥" },
  "Jayson Tatum": { full: "杰森·塔图姆", short: "塔图姆" },
  "Joel Embiid": { full: "乔尔·恩比德", short: "恩比德" },
  "Shai Gilgeous-Alexander": { full: "谢伊·吉尔杰斯-亚历山大", short: "亚历山大", aliases: ["SGA"] },
  "Anthony Davis": { full: "安东尼·戴维斯", short: "戴维斯", aliases: ["AD"] },
  "James Harden": { full: "詹姆斯·哈登", short: "哈登" },
  "Kyrie Irving": { full: "凯里·欧文", short: "欧文" },
  "Devin Booker": { full: "德文·布克", short: "布克" },
  "Damian Lillard": { full: "达米安·利拉德", short: "利拉德" },
  "Kawhi Leonard": { full: "科怀·伦纳德", short: "伦纳德" },
  "Paul George": { full: "保罗·乔治", short: "乔治" },
  "Jimmy Butler": { full: "吉米·巴特勒", short: "巴特勒" },
  "Zion Williamson": { full: "锡安·威廉森", short: "锡安" },
  "Ja Morant": { full: "贾·莫兰特", short: "莫兰特" },
  "Victor Wembanyama": { full: "维克托·文班亚马", short: "文班亚马" },
};

const warnedMissing = new Set<string>();

function normalizeName(name: string) {
  return name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function buildLookup(source: Record<string, NameTranslation>) {
  const lookup = new Map<string, NameTranslation>();
  Object.entries(source).forEach(([name, translation]) => {
    [name, ...(translation.aliases ?? [])].forEach((alias) => {
      lookup.set(normalizeName(alias), translation);
    });
  });
  return lookup;
}

const teamLookup = buildLookup(TEAM_NAME_TRANSLATIONS);
const playerLookup = buildLookup(PLAYER_NAME_TRANSLATIONS);

function translateName(name: string | null | undefined, mode: NameTranslationMode, lookup: Map<string, NameTranslation>, type: "team" | "player") {
  if (!name) {
    return "";
  }
  if (mode === "original") {
    return name;
  }

  const translation = lookup.get(normalizeName(name));
  if (!translation) {
    const warningKey = `${type}:${name}`;
    if (!warnedMissing.has(warningKey) && typeof console !== "undefined") {
      warnedMissing.add(warningKey);
      console.info(`[nameTranslations] missing ${type} translation: ${name}`);
    }
    return name;
  }

  return translation[mode];
}

export function translateTeamName(name: string | null | undefined, mode: NameTranslationMode = "full") {
  return translateName(name, mode, teamLookup, "team");
}

export function translatePlayerName(name: string | null | undefined, mode: NameTranslationMode = "full") {
  return translateName(name, mode, playerLookup, "player");
}

export function formatTeamName(name: string | null | undefined) {
  return translateTeamName(name, "full");
}

export function formatPlayerName(name: string | null | undefined) {
  return translatePlayerName(name, "full");
}

export function translateKnownNamesInText(text: string, mode: NameTranslationMode = "full") {
  if (mode === "original") {
    return text;
  }

  let result = text;
  const replacements = [
    ...Object.entries(TEAM_NAME_TRANSLATIONS).flatMap(([name, translation]) => [name, ...(translation.aliases ?? [])].map((alias) => [alias, translation[mode]] as const)),
    ...Object.entries(PLAYER_NAME_TRANSLATIONS).flatMap(([name, translation]) => [name, ...(translation.aliases ?? [])].map((alias) => [alias, translation[mode]] as const)),
  ].sort((a, b) => b[0].length - a[0].length);

  replacements.forEach(([from, to]) => {
    result = result.replace(new RegExp(`\\b${from.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g"), to);
  });

  return result;
}
