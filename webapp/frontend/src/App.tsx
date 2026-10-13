import { ActionIcon, Alert, AppShell, Badge, Button, Group, NavLink, Text, Tooltip, useMantineColorScheme } from "@mantine/core";
import {
  IconArchive, IconBrandGit, IconFileText, IconListDetails, IconMoon, IconRefresh, IconSitemap, IconSun, IconTerminal2,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, createBrowserRouter, useLocation, useRouteError } from "react-router-dom";

import { post } from "./api/client";
import { useEngine, useGitStatus } from "./api/hooks";
import { ArchivePage, RunPage } from "./pages/ArchivePage";
import { GitPage } from "./pages/GitPage";
import { JobsPage } from "./pages/JobsPage";
import { ModulePage } from "./pages/ModulePage";
import { SheetEditorPage } from "./pages/SheetEditorPage";
import { SheetsPage } from "./pages/SheetsPage";
import { TaskEditorPage } from "./pages/TaskEditorPage";
import { TasksPage } from "./pages/TasksPage";
import { TopicsPage } from "./pages/TopicsPage";

const NAV = [
  { to: "/tasks", label: "Tasks", icon: IconListDetails },
  { to: "/sheets", label: "Sheets", icon: IconFileText },
  { to: "/archive", label: "Archive", icon: IconArchive },
  { to: "/topics", label: "Topics", icon: IconSitemap },
  { to: "/git", label: "Git", icon: IconBrandGit },
  { to: "/jobs", label: "Jobs", icon: IconTerminal2 },
];

const STATE_COLOR: Record<string, string> = { ready: "green", busy: "blue", starting: "yellow", stale: "yellow", stopped: "gray" };

function EngineBadge() {
  const { data, error } = useEngine();
  const qc = useQueryClient();
  if (error) return <Badge color="red">API offline</Badge>;
  if (!data) return null;
  const nErr = Object.keys(data.import_errors ?? {}).length;
  return (
    <Group gap={6}>
      <Tooltip label={`engine pid ${data.pid ?? "—"}, ${data.restarts} restart(s), ${data.tasks ?? "?"} tasks`}>
        <Badge color={STATE_COLOR[data.state] ?? "gray"} variant="light">engine {data.state}{data.version ? ` · ${data.version}` : ""}</Badge>
      </Tooltip>
      {nErr > 0 && <Badge color="red" component={Link} to="/tasks" style={{ cursor: "pointer" }}>{nErr} import error(s)</Badge>}
      <Tooltip label={data.latex.reachable ? "latex-worker reachable" : "PDF builds unavailable"}>
        <Badge color={data.latex.reachable ? "green" : "red"} variant="light">latex</Badge>
      </Tooltip>
      <Tooltip label="restart engine worker">
        <ActionIcon size="sm" variant="subtle" onClick={async () => {
          await post("/engine/restart");
          qc.invalidateQueries();
        }}><IconRefresh size={14} /></ActionIcon>
      </Tooltip>
    </Group>
  );
}

function Shell() {
  const loc = useLocation();
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  const { data: git } = useGitStatus();
  return (
    <AppShell header={{ height: 48 }} navbar={{ width: 170, breakpoint: 0 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Text fw={700} component={Link} to="/" style={{ textDecoration: "none", color: "inherit" }}>taskgen</Text>
            <Text size="sm" c="dimmed">Компьютерная алгебра — задачи и листы</Text>
          </Group>
          <Group gap="sm">
            <EngineBadge />
            <ActionIcon variant="subtle" onClick={() => setColorScheme(colorScheme === "dark" ? "light" : "dark")}>
              {colorScheme === "dark" ? <IconSun size={16} /> : <IconMoon size={16} />}
            </ActionIcon>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="xs">
        {NAV.map((n) => (
          <NavLink key={n.to} component={Link} to={n.to} label={n.label} leftSection={<n.icon size={16} />}
            active={loc.pathname.startsWith(n.to)}
            rightSection={n.to === "/git" && git?.files.length ? <Badge size="xs" color={git.dirty ? "orange" : "gray"}>{git.files.length}</Badge> : null} />
        ))}
      </AppShell.Navbar>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}

function RouteError() {
  const err = useRouteError() as Error;
  return (
    <Alert color="red" title="This page crashed" m="md">
      <Text size="sm">{err?.message ?? String(err)}</Text>
      <Button size="xs" mt="sm" variant="light" onClick={() => window.location.reload()}>Reload</Button>
    </Alert>
  );
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Shell />,
    children: [{ errorElement: <RouteError />, children: [
      { index: true, element: <TasksPage /> },
      { path: "tasks", element: <TasksPage /> },
      { path: "tasks/:id", element: <TaskEditorPage /> },
      { path: "modules", element: <ModulePage /> },
      { path: "sheets", element: <SheetsPage /> },
      { path: "sheets/*", element: <SheetEditorPage /> },
      { path: "archive", element: <ArchivePage /> },
      { path: "archive/:sheet/:run", element: <RunPage /> },
      { path: "topics", element: <TopicsPage /> },
      { path: "git", element: <GitPage /> },
      { path: "jobs", element: <JobsPage /> },
    ] }],
  },
]);


