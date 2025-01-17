CREATE TABLE `accomodation` (
	`id`	int	NOT NULL,
	`spot_common_id`	int	NOT NULL,
	`accomodation_type`	AccomodationType	NULL,
	`phone_number`	varchar(30)	NULL,
	`business_status`	varchar(30)	NULL,
	`business_hours`	varchar(30)	NULL	COMMENT 'str'
);

CREATE TABLE `cafe` (
	`id`	int	NOT NULL,
	`spot_common_id`	int	NOT NULL,
	`cafe_type_id`	int	NULL,
	`phone_number`	varchar(30)	NULL,
	`business_status`	varchar(30)	NULL,
	`business_hours`	varchar(30)	NULL	COMMENT 'str'
);

CREATE TABLE `site` (
	`id`	int	NOT NULL,
	`spot_common_id`	int	NOT NULL,
	`spot_type`	SpotType	NULL,
	`phone_number`	varchar(30)	NULL,
	`business_status`	varchar(30)	NULL,
	`business_hours`	varchar(30)	NULL	COMMENT 'str'
);

CREATE TABLE `restaurant_type` (
	`id`	int	NOT NULL,
	`type_eng`	varchar(100)	NULL,
	`type_kor`	varchar(100)	NULL
);

CREATE TABLE `spot_common` (
	`spot_common_id`	int	NOT NULL,
	`kor_name`	varchar(255)	NOT NULL,
	`eng_name`	varchar(255)	NULL,
	`description`	varchar(255)	NOT NULL,
	`url`	varchar(2083)	NULL,
	`image_url`	varchar(2083)	NOT NULL,
	`map_url`	varchar(2083)	NOT NULL,
	`likes`	int	NULL,
	`satisfaction`	float	NULL,
	`created_at`	datetime	NULL,
	`updated_at`	datetime	NULL
);

CREATE TABLE `cafe_type` (
	`int`	int	NOT NULL,
	`type_kor`	varchar(255)	NULL,
	`type_eng`	varchar(255)	NULL
);

CREATE TABLE `tag` (
	`tag_id`	int	NOT NULL,
	`eng_name`	varchar(20)	NULL,
	`kor_name`	varchar(20	NULL
);

CREATE TABLE `spot_common_tag_map` (
	`spot_common_id`	int	NOT NULL,
	`tag_id`	int	NOT NULL
);

CREATE TABLE `cafe_type_map` (
	`cafe_id`	int	NOT NULL,
	`type_id`	int	NOT NULL
);

CREATE TABLE `restaurant` (
	`id`	VARCHAR(255)	NOT NULL	DEFAULT int,
	`spot_common_id`	int	NOT NULL	DEFAULT int,
	`phone_number`	VARCHAR(255)	NULL	DEFAULT varchar(20),
	`business_status`	VARCHAR(255)	NULL	DEFAULT varchar(100),
	`business_hours`	VARCHAR(255)	NULL	DEFAULT varchar(100),
	`created_at`	VARCHAR(255)	NULL	DEFAULT datetime,
	`updated_at`	VARCHAR(255)	NULL	DEFAULT datetime
);

CREATE TABLE `restaurant_type_map` (
	`restaurant_id`	VARCHAR(255)	NOT NULL	DEFAULT int,
	`type_id`	int	NOT NULL
);

CREATE TABLE `plan` (
	`id`	int	NOT NULL,
	`member_id`	int	NOT NULL,
	`memberId`	int	NULL,
	`plan_name`	varchar(255)	NULL,
	`start_date`	datetime	NULL,
	`end_date`	datetime	NULL,
	`main_location`	str	NULL,
	`ages`	int	NULL,
	`companion_count`	int	NULL,
	`plan_concepts`	int	NULL,
	`plan_elements`	int	NULL
);

CREATE TABLE `accomodation_type` (
	`id`	int	NOT NULL,
	`type_eng`	varchar(100)	NULL,
	`type_kor`	varchar(100)	NULL
);

CREATE TABLE `plan_spot_common_map` (
	`id`	int	NOT NULL,
	`spot_common_id`	int	NOT NULL
);

CREATE TABLE `accomodation_type_map` (
	`id`	int	NOT NULL,
	`type_id`	int	NOT NULL
);

CREATE TABLE `checklist` (
	`plan_id`	int	NOT NULL,
	`item`	varchar(255)	NULL,
	`state`	bool	NULL
);

CREATE TABLE `member` (
	`id`	int	NOT NULL,
	`nickname`	varchar(255)	NULL,
	`name`	int	NOT NULL,
	`email`	varchar(100)	NOT NULL,
	`sex`	char(10)	NULL,
	`picture_url`	varchar(2083)	NULL,
	`birth`	date	NOT NULL,
	`street`	varchar(255)	NULL,
	`dong`	varchar(255)	NULL,
	`si`	varchar(255)	NULL,
	`doh`	varchar(255)	NULL,
	`zip`	char(10)	NULL,
	`phone_number`	varchar(20)	NULL,
	`voice`	varchar(255)	NULL,
	`card_number`	varchar(255)	NULL,
	`expiry_date`	varchar(255)	NULL,
	`cvv`	varchar(255)	NULL,
	`cardholder_name`	varchar(255)	NULL,
	`role`	varchar(10)	NULL,
	`created_at`	datetime	NULL,
	`updated_at`	datetime	NULL
);

CREATE TABLE `site type map` (
	`id`	int	NOT NULL,
	`id2`	int	NOT NULL
);

CREATE TABLE `site type` (
	`id`	int	NOT NULL,
	`type_eng`	varchar(100)	NULL,
	`type_kor`	varchar(100)	NULL
);

ALTER TABLE `accomodation` ADD CONSTRAINT `PK_ACCOMODATION` PRIMARY KEY (
	`id`,
	`spot_common_id`
);

ALTER TABLE `cafe` ADD CONSTRAINT `PK_CAFE` PRIMARY KEY (
	`id`,
	`spot_common_id`
);

ALTER TABLE `site` ADD CONSTRAINT `PK_SITE` PRIMARY KEY (
	`id`,
	`spot_common_id`
);

ALTER TABLE `restaurant_type` ADD CONSTRAINT `PK_RESTAURANT_TYPE` PRIMARY KEY (
	`id`
);

ALTER TABLE `spot_common` ADD CONSTRAINT `PK_SPOT_COMMON` PRIMARY KEY (
	`spot_common_id`
);

ALTER TABLE `cafe_type` ADD CONSTRAINT `PK_CAFE_TYPE` PRIMARY KEY (
	`int`
);

ALTER TABLE `tag` ADD CONSTRAINT `PK_TAG` PRIMARY KEY (
	`tag_id`
);

ALTER TABLE `spot_common_tag_map` ADD CONSTRAINT `PK_SPOT_COMMON_TAG_MAP` PRIMARY KEY (
	`spot_common_id`,
	`tag_id`
);

ALTER TABLE `cafe_type_map` ADD CONSTRAINT `PK_CAFE_TYPE_MAP` PRIMARY KEY (
	`cafe_id`,
	`type_id`
);

ALTER TABLE `restaurant` ADD CONSTRAINT `PK_RESTAURANT` PRIMARY KEY (
	`id`,
	`spot_common_id`
);

ALTER TABLE `restaurant_type_map` ADD CONSTRAINT `PK_RESTAURANT_TYPE_MAP` PRIMARY KEY (
	`restaurant_id`,
	`type_id`
);

ALTER TABLE `plan` ADD CONSTRAINT `PK_PLAN` PRIMARY KEY (
	`id`,
	`member_id`
);

ALTER TABLE `accomodation_type` ADD CONSTRAINT `PK_ACCOMODATION_TYPE` PRIMARY KEY (
	`id`
);

ALTER TABLE `plan_spot_common_map` ADD CONSTRAINT `PK_PLAN_SPOT_COMMON_MAP` PRIMARY KEY (
	`id`
);

ALTER TABLE `accomodation_type_map` ADD CONSTRAINT `PK_ACCOMODATION_TYPE_MAP` PRIMARY KEY (
	`id`,
	`type_id`
);

ALTER TABLE `checklist` ADD CONSTRAINT `PK_CHECKLIST` PRIMARY KEY (
	`plan_id`
);

ALTER TABLE `member` ADD CONSTRAINT `PK_MEMBER` PRIMARY KEY (
	`id`
);

ALTER TABLE `site type map` ADD CONSTRAINT `PK_SITE TYPE MAP` PRIMARY KEY (
	`id`,
	`id2`
);

ALTER TABLE `site type` ADD CONSTRAINT `PK_SITE TYPE` PRIMARY KEY (
	`id`
);

ALTER TABLE `accomodation` ADD CONSTRAINT `FK_spot_common_TO_accomodation_1` FOREIGN KEY (
	`spot_common_id`
)
REFERENCES `spot_common` (
	`spot_common_id`
);

ALTER TABLE `cafe` ADD CONSTRAINT `FK_spot_common_TO_cafe_1` FOREIGN KEY (
	`spot_common_id`
)
REFERENCES `spot_common` (
	`spot_common_id`
);

ALTER TABLE `site` ADD CONSTRAINT `FK_spot_common_TO_site_1` FOREIGN KEY (
	`spot_common_id`
)
REFERENCES `spot_common` (
	`spot_common_id`
);

ALTER TABLE `spot_common_tag_map` ADD CONSTRAINT `FK_spot_common_TO_spot_common_tag_map_1` FOREIGN KEY (
	`spot_common_id`
)
REFERENCES `spot_common` (
	`spot_common_id`
);

ALTER TABLE `spot_common_tag_map` ADD CONSTRAINT `FK_tag_TO_spot_common_tag_map_1` FOREIGN KEY (
	`tag_id`
)
REFERENCES `tag` (
	`tag_id`
);

ALTER TABLE `cafe_type_map` ADD CONSTRAINT `FK_cafe_TO_cafe_type_map_1` FOREIGN KEY (
	`cafe_id`
)
REFERENCES `cafe` (
	`id`
);

ALTER TABLE `cafe_type_map` ADD CONSTRAINT `FK_cafe_type_TO_cafe_type_map_1` FOREIGN KEY (
	`type_id`
)
REFERENCES `cafe_type` (
	`int`
);

ALTER TABLE `restaurant` ADD CONSTRAINT `FK_spot_common_TO_restaurant_1` FOREIGN KEY (
	`spot_common_id`
)
REFERENCES `spot_common` (
	`spot_common_id`
);

ALTER TABLE `restaurant_type_map` ADD CONSTRAINT `FK_restaurant_TO_restaurant_type_map_1` FOREIGN KEY (
	`restaurant_id`
)
REFERENCES `restaurant` (
	`id`
);

ALTER TABLE `restaurant_type_map` ADD CONSTRAINT `FK_restaurant_type_TO_restaurant_type_map_1` FOREIGN KEY (
	`type_id`
)
REFERENCES `restaurant_type` (
	`id`
);

ALTER TABLE `plan` ADD CONSTRAINT `FK_member_TO_plan_1` FOREIGN KEY (
	`member_id`
)
REFERENCES `member` (
	`id`
);

ALTER TABLE `plan_spot_common_map` ADD CONSTRAINT `FK_plan_TO_plan_spot_common_map_1` FOREIGN KEY (
	`id`
)
REFERENCES `plan` (
	`id`
);

ALTER TABLE `accomodation_type_map` ADD CONSTRAINT `FK_accomodation_TO_accomodation_type_map_1` FOREIGN KEY (
	`id`
)
REFERENCES `accomodation` (
	`id`
);

ALTER TABLE `accomodation_type_map` ADD CONSTRAINT `FK_accomodation_type_TO_accomodation_type_map_1` FOREIGN KEY (
	`type_id`
)
REFERENCES `accomodation_type` (
	`id`
);

ALTER TABLE `checklist` ADD CONSTRAINT `FK_plan_TO_checklist_1` FOREIGN KEY (
	`plan_id`
)
REFERENCES `plan` (
	`id`
);

ALTER TABLE `site type map` ADD CONSTRAINT `FK_site_TO_site type map_1` FOREIGN KEY (
	`id`
)
REFERENCES `site` (
	`id`
);

ALTER TABLE `site type map` ADD CONSTRAINT `FK_site type_TO_site type map_1` FOREIGN KEY (
	`id2`
)
REFERENCES `site type` (
	`id`
);

