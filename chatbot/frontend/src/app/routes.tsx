import * as React from 'react';
import { Route, Routes } from 'react-router-dom';
// import { Dashboard } from '@app/Dashboard/Dashboard';
import { Chat } from '@app/Chat/Chat';
import { GeneralSettings } from '@app/Settings/General/GeneralSettings';
import { ProfileSettings } from '@app/Settings/Profile/ProfileSettings';
import { NotFound } from '@app/NotFound/NotFound';

export interface IAppRoute {
  label?: string; // Excluding the label will exclude the route from the nav sidebar in AppLayout
  element: React.ReactElement;
  exact?: boolean;
  path: string;
  title: string;
  routes?: undefined;
}

export interface IAppRouteGroup {
  label: string;
  routes: IAppRoute[];
}

export type AppRouteConfig = IAppRoute | IAppRouteGroup;

const routes: AppRouteConfig[] = [
  // {
  //   element: <Dashboard />,
  //   exact: true,
  //   label: 'Dashboard',
  //   path: '/',
  //   title: 'Chatbot | Dashboard',
  // },
  {
    element: <Chat />,
    exact: true,
    label: 'Chat',
    path: '/',
    title: 'Chatbot | Chat',
  },
  {
    element: <Chat />,
    exact: true,
    // label: 'Chat', // Removing duplicate nav item
    path: '/chat',
    title: 'Chatbot | Chat',
  },
  {
    label: 'Settings',
    routes: [
      {
        element: <GeneralSettings />,
        exact: true,
        label: 'General',
        path: '/settings/general',
        title: 'Chatbot | General Settings',
      },
      {
        element: <ProfileSettings />,
        exact: true,
        label: 'Profile',
        path: '/settings/profile',
        title: 'Chatbot | Profile Settings',
      },
    ],
  },
];

const flattenedRoutes: IAppRoute[] = routes.reduce(
  (flattened, route) => [...flattened, ...(route.routes ? route.routes : [route])],
  [] as IAppRoute[],
);

const AppRoutes = (): React.ReactElement => (
  <Routes>
    {flattenedRoutes.map(({ path, element }, idx) => (
      <Route path={path} element={element} key={idx} />
    ))}
    <Route element={<NotFound />} />
  </Routes>
);

export { AppRoutes, routes };
