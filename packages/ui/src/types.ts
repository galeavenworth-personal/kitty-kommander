export type ProjectStats = {
  total: number;
  closed: number;
  blocked: number;
  in_progress: number;
  open: number;
};

export type ReadyItem = {
  id: string;
  title: string;
  priority: number;
};

export type Commit = {
  hash: string;
  message: string;
};

export type BeadsFixture = {
  stats?: ProjectStats;
  ready?: ReadyItem[];
  commits?: Commit[];
};
