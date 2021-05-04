/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import React from 'react';
import { shallow } from 'enzyme';

import thunk from 'redux-thunk';
import { styledMount as mount } from 'spec/helpers/theming';
import configureStore from 'redux-mock-store';
import { Provider } from 'react-redux';

import { ExploreChartHeader } from 'src/explore/components/ExploreChartHeader';
import ExploreActionButtons from 'src/explore/components/ExploreActionButtons';
import EmbedCodeButton from 'src/explore/components/EmbedCodeButton';

import FaveStar from 'src/components/FaveStar';
import EditableTitle from 'src/components/EditableTitle';
import URLShortLinkButton from 'src/components/URLShortLinkButton';

const saveSliceStub = jest.fn();
const updateChartTitleStub = jest.fn();
const mockProps = {
  actions: {
    saveSlice: saveSliceStub,
    updateChartTitle: updateChartTitleStub,
  },
  canFavstar: true,
  canShare: true,
  canSqllab: true,
  can_overwrite: true,
  can_download: true,
  isStarred: true,
  slice: {
    form_data: {
      viz_type: 'line',
    },
  },
  table_name: 'foo',
  form_data: {
    viz_type: 'table',
  },
  timeout: 1000,
  chart: {
    id: 0,
    queryResponse: {},
    latestQueryFormData: {
      datasource: '1__table',
    },
  },
  chartHeight: '30px',
};

const mockStore = configureStore([thunk]);
const store = mockStore({});

describe('ExploreChartHeader', () => {
  let wrapper;
  beforeEach(() => {
    wrapper = shallow(<ExploreChartHeader {...mockProps} />);
  });

  it('is valid', () => {
    expect(React.isValidElement(<ExploreChartHeader {...mockProps} />)).toBe(
      true,
    );
  });

  it('renders', () => {
    expect(wrapper.find(EditableTitle)).toExist();
    expect(wrapper.find(ExploreActionButtons)).toExist();
  });

  describe('ExploreChartHeader with permissions', () => {
    it('renders with all links', () => {
      // TODO CSV link
      const props = JSON.parse(JSON.stringify(mockProps));
      const store = mockStore(props);

      const tmpWrapper = mount(
        <Provider store={store}>
          <ExploreChartHeader {...props} />
        </Provider>,
      );

      expect(tmpWrapper.find('[data-test="sqllab-menu-item"]').exists()).toBe(
        true,
      );
      expect(
        tmpWrapper.find('[data-test="edit-properties-menu-item"]'),
      ).toExist();
      expect(tmpWrapper.find(URLShortLinkButton).exists()).toBe(true);
      expect(tmpWrapper.find(EmbedCodeButton).exists()).toBe(true);
      expect(tmpWrapper.find(FaveStar).exists()).toBe(true);
    });

    it('renders without sqllab', () => {
      const props = JSON.parse(JSON.stringify(mockProps));
      props.canSqllab = false;
      const store = mockStore(props);

      const tmpWrapper = mount(
        <Provider store={store}>
          <ExploreChartHeader {...props} />
        </Provider>,
      );

      expect(tmpWrapper.find('[data-test="sqllab-menu-item"]').exists()).toBe(
        false,
      );
      expect(
        tmpWrapper.find('[data-test="edit-properties-menu-item"]'),
      ).toExist();
      expect(tmpWrapper.find(URLShortLinkButton).exists()).toBe(true);
      expect(tmpWrapper.find(EmbedCodeButton).exists()).toBe(true);
      expect(tmpWrapper.find(FaveStar).exists()).toBe(true);
    });

    it('renders without shorten and share link', () => {
      const props = JSON.parse(JSON.stringify(mockProps));
      props.canShare = false;

      const tmpWrapper = mount(
        <Provider store={store}>
          <ExploreChartHeader {...props} />
        </Provider>,
      );

      expect(tmpWrapper.find(URLShortLinkButton).exists()).toBe(false);
      expect(tmpWrapper.find(EmbedCodeButton).exists()).toBe(false);
      expect(tmpWrapper.find(FaveStar).exists()).toBe(true);
      expect(tmpWrapper.find('[data-test="sqllab-menu-item"]').exists()).toBe(
        true,
      );
      expect(
        tmpWrapper.find('[data-test="edit-properties-menu-item"]'),
      ).toExist();
    });

    it('renders without favstar button', () => {
      const props = JSON.parse(JSON.stringify(mockProps));
      props.canFavstar = false;

      const tmpWrapper = mount(
        <Provider store={store}>
          <ExploreChartHeader {...props} />
        </Provider>,
      );

      expect(tmpWrapper.find(FaveStar).exists()).toBe(false);
    });

    it('renders without shorten, share link, sqllab and edit properties', () => {
      const props = JSON.parse(JSON.stringify(mockProps));
      props.canShare = false;
      props.canSqllab = false;
      props.can_overwrite = false;
      props.canFavstar = false;

      const tmpWrapper = mount(
        <Provider store={store}>
          <ExploreChartHeader {...props} />
        </Provider>,
      );

      expect(tmpWrapper.find(URLShortLinkButton).exists()).toBe(false);
      expect(tmpWrapper.find(EmbedCodeButton).exists()).toBe(false);
      expect(tmpWrapper.find(FaveStar).exists()).toBe(false);
      expect(tmpWrapper.find('[data-test="sqllab-menu-item"]').exists()).toBe(
        false,
      );
      expect(
        tmpWrapper.find('[data-test="edit-properties-menu-item"]').exists(),
      ).toBe(false);
    });

    it('should update title but not save', () => {
      const editableTitle = wrapper.find(EditableTitle);
      expect(editableTitle.props().onSaveTitle).toBe(updateChartTitleStub);
    });
  });
});
