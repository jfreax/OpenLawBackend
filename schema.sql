drop table if exists Laws;
create table Laws (
  id integer primary key autoincrement,
  slug text not null,
  short_name text not null,
  long_name text not null
);


drop table if exists Law_Text;
create table Law_Text (
  id integer,
  law_id integer not null,
  text text not null,

  CONSTRAINT pk_law_text_id PRIMARY KEY (id, law_id),
  FOREIGN KEY (law_id) REFERENCES Laws(id)
);
 