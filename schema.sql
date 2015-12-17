drop table if exists pxeitems;
create table pxeitems (
  id integer primary key autoincrement,
  pxe_title text not null,
  pxe_comment text,
  unix_time text not null,
  random_str text not null,
  repo_url text not null,
  repo_kernel text not null,
  repo_initrd text not null,
  inst_flag text not null
);
