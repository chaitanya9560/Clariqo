-- Private per-account study state. No service-role key is needed by the app.
create table if not exists public.clariqo_learning (
  user_id uuid primary key references auth.users(id) on delete cascade,
  data jsonb not null check (jsonb_typeof(data) = 'object' and octet_length(data::text) <= 2097152),
  revision integer not null default 1 check (revision > 0),
  updated_at timestamptz not null default now()
);
create table if not exists public.clariqo_materials (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 200),
  size bigint not null check (size between 1 and 20971520),
  page_count integer not null check (page_count between 1 and 200),
  chunks jsonb not null check (jsonb_typeof(chunks) = 'array' and jsonb_array_length(chunks) <= 1000 and octet_length(chunks::text) <= 2097152),
  storage_path text not null check (storage_path like (user_id::text || '/' || id::text || '/%')),
  created_at timestamptz not null default now(),
  unique (user_id, name)
);
create index if not exists clariqo_materials_user_id_idx on public.clariqo_materials(user_id);
alter table public.clariqo_learning enable row level security;
alter table public.clariqo_learning force row level security;
alter table public.clariqo_materials enable row level security;
alter table public.clariqo_materials force row level security;
revoke all on public.clariqo_learning, public.clariqo_materials from public, anon;
grant select, insert, update, delete on public.clariqo_learning, public.clariqo_materials to authenticated;

create policy learning_select_own on public.clariqo_learning for select to authenticated using ((select auth.uid()) = user_id);
create policy learning_insert_own on public.clariqo_learning for insert to authenticated with check ((select auth.uid()) = user_id);
create policy learning_update_own on public.clariqo_learning for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy learning_delete_own on public.clariqo_learning for delete to authenticated using ((select auth.uid()) = user_id);
create policy materials_select_own on public.clariqo_materials for select to authenticated using ((select auth.uid()) = user_id);
create policy materials_insert_own on public.clariqo_materials for insert to authenticated with check ((select auth.uid()) = user_id);
create policy materials_update_own on public.clariqo_materials for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy materials_delete_own on public.clariqo_materials for delete to authenticated using ((select auth.uid()) = user_id);

create or replace function public.clariqo_material_limits() returns trigger
language plpgsql security invoker set search_path = '' as $$
declare file_count integer; total_size bigint;
begin
  if (select auth.uid()) is null or (select auth.uid()) <> new.user_id then
    raise exception 'Only the owner can save a study material';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.user_id::text, 0));
  select count(*), coalesce(sum(size), 0) into file_count, total_size
    from public.clariqo_materials where user_id = new.user_id and id <> new.id;
  if file_count >= 5 or total_size + new.size > 52428800 then
    raise exception 'Each account allows 5 PDFs and 50 MB of study material';
  end if;
  return new;
end;
$$;
revoke all on function public.clariqo_material_limits() from public, anon, authenticated;
create trigger clariqo_material_limits before insert or update on public.clariqo_materials
for each row execute function public.clariqo_material_limits();

create or replace function public.clariqo_learning_timestamp() returns trigger
language plpgsql security invoker set search_path = '' as $$
begin new.updated_at = now(); return new; end;
$$;
revoke all on function public.clariqo_learning_timestamp() from public, anon, authenticated;
create trigger clariqo_learning_timestamp before update on public.clariqo_learning
for each row execute function public.clariqo_learning_timestamp();

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('study-pdfs', 'study-pdfs', false, 20971520, array['application/pdf']);
create policy pdf_select_own on storage.objects for select to authenticated
using (bucket_id = 'study-pdfs' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy pdf_insert_own on storage.objects for insert to authenticated
with check (bucket_id = 'study-pdfs' and (storage.foldername(name))[1] = (select auth.uid())::text
  and array_length(storage.foldername(name), 1) = 2 and storage.extension(name) = 'pdf');
create policy pdf_delete_own on storage.objects for delete to authenticated
using (bucket_id = 'study-pdfs' and (storage.foldername(name))[1] = (select auth.uid())::text);
-- New versions use new object names: no Storage UPDATE policy or upsert is needed.
