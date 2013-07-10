drop table if exists Laws;
create table Laws (
  id integer primary key autoincrement,
  slug text not null,
  short_name text not null,
  long_name text not null
);


drop table if exists Law_Heads;
create table Law_Heads (
  id integer not null,
  law_id integer not null,
  headline text not null,
  depth integer not null,
  CONSTRAINT pk_law_text_id PRIMARY KEY (id, law_id),
  FOREIGN KEY (law_id) REFERENCES Laws(id)
);
 

drop table if exists Law_Texts;
create table Law_Texts (
  id integer,
  head_id integer not null,
  text text not null,

  CONSTRAINT pk_law_head_id PRIMARY KEY (id, head_id),
  FOREIGN KEY (head_id) REFERENCES Law_Heads(id)
);
 